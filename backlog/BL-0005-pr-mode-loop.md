# BL-0005: Make the loop pull-request-based so CODEOWNERS binds

- Status: RESCINDED 2026-08-09 by ADR-0009 — do not resume. Steps 1 and 2 were
  drafted 2026-08-08, applied to `main` (PR #5, `8906f4f`), and then reverted
  when the human operator decided the agent owns forward motion and no
  pull-request gate belongs in the loop. Step 3 was never applied. The drafted
  patches and the revert patch remain under `core_change_requests/patches/` as
  the record.
- Priority: none (rescinded)
- Requires sealed changes: no
- Requires protected-path changes: yes (`loop/`, `.github/`) — human applies
- Origin: adversarial review of the branch-protection options, 2026-08-08

## Why

`CODEOWNERS` currently enforces nothing. It binds only through a required
pull-request review, and that requirement is off because `loop/run_session.sh`
pushes to `main` directly. See ADR-0008 "Enforcement reality".

The asymmetry this leaves: history rewriting is impossible (server-side
rulesets), but a bad *forward* commit — tampered `results/`, a rewritten
ledger line — is caught only by `loop/validate_session.sh`, which the session
itself could in principle reach. Moving to pull requests replaces
self-policing with a server-side gate that fails closed.

## What changes

1. `loop/run_session.sh`: on validation pass, push `session/<id>` and open a
   pull request against `main` instead of merging locally and pushing. Do not
   delete the branch. The runner's job ends at "PR opened"; merging is the
   gate's job, not the runner's.
2. New `.github/workflows/session-validate.yml`, triggered on `pull_request`,
   that runs `loop/validate_session.sh` **checked out from the base ref**
   (`github.event.pull_request.base.sha`), not from the PR head, and reports a
   named check. Reading it from the head would reintroduce the
   judge-yourself hole that BL-0005's sibling fix closed in the runner.
3. Branch ruleset `main history protection` gains:
   - Require a pull request before merging (1 approval)
   - Require review from Code Owners
   - Require status checks to pass, naming the check from step 2
4. The runner keeps the default `GITHUB_TOKEN`, so pull requests are authored
   by `github-actions[bot]`. This matters: GitHub forbids a pull request's
   author from supplying its required approving review, so a PR authored by
   the human's own identity could never be approved by the human and the gate
   would degrade into routine admin bypass.

## Ordering constraint

Step 3 must land **after** steps 1 and 2, and after the runner fix that pushes
before deleting the session branch. Enabling the pull-request requirement
against the current runner does not gate sessions — it destroys them, because
the rejected push is swallowed as a warning after the branch is already gone.

## Drafted 2026-08-08: patches for steps 1 and 2

`core_change_requests/2026-08-08-pr-mode-loop.md` carries both patches, verified
with `git apply --check`. Five things this item does not say came out of writing
them; two would have deadlocked the loop, and the change request states them in
full. In short:

1. The default `GITHUB_TOKEN` cannot trigger the required check — GitHub does not
   run workflows on events it creates. Step 4 of this item is right that the
   author must not be the human, but the token has to be a GitHub App or
   machine-account one for both halves to hold.
2. `session.yml` grants only `contents: write`; opening a pull request also needs
   `pull-requests: write`.
3. The `GITHUB_TOKEN` fallback additionally needs "Allow GitHub Actions to create
   and approve pull requests" enabled in repository settings.
4. The salvage path pushes `main` directly, which step 3 would refuse — stranding
   the journal of every failed session off `main` and making exit criterion 2
   unreachable. The salvage has to travel a pull request too.
5. The required check cannot run the full validator on a salvage branch (it
   failed validation by construction, so the check would always be red), and must
   pass ordinary human pull requests, or it blocks the very changes that repair
   the loop.

## Definition of done

A session runs unattended, opens a pull request, the named check reports, the
human approves and merges, and a session that modifies a protected path is
blocked by the check rather than by the runner's own validator. Record the
result in a journal entry and update ADR-0008's "Enforcement reality" section
to move `CODEOWNERS` from "not in effect" to "binding".
