# BL-0005: Make the loop pull-request-based so CODEOWNERS binds

- Status: open
- Priority: 5 (do before claiming exit criterion 1)
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

## Definition of done

A session runs unattended, opens a pull request, the named check reports, the
human approves and merges, and a session that modifies a protected path is
blocked by the check rather than by the runner's own validator. Record the
result in a journal entry and update ADR-0008's "Enforcement reality" section
to move `CODEOWNERS` from "not in effect" to "binding".
