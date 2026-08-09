# CCR 2026-08-08: make the loop pull-request-based (BL-0005)

> **WITHDRAWN 2026-08-09 by ADR-0009.** This request was applied to `main`
> (PR #5, `8906f4f`) and then reverted: the human operator decided the agent
> owns the repository's forward motion, so no pull-request gate belongs in
> the loop. Do not re-apply the patches below. They, and the revert patch
> `patches/2026-08-09-rescind-pr-mode.diff`, are retained as the record of
> the road not taken — including the five findings, which stay true and
> matter to anyone who ever revisits this design.

- Origin: `backlog/BL-0005-pr-mode-loop.md`, drafted in a supervised session
  2026-08-08 at the human's request
- Requires sealed changes: no
- Requires protected-path changes: yes (`loop/`, `.github/`) — human applies
- Related: `docs/adr/0008-mvp-reduction.md` ("Enforcement reality"),
  `backlog/BL-0006-scope-agent-deny-rules.md`

## What this implements

BL-0005 steps 1 and 2. Step 3 is a GitHub settings change and is described at
the end; it must be applied last.

- **Patch 1** — `core_change_requests/patches/2026-08-08-pr-mode-1-runner.diff`
  (verified with `git apply --check`). `loop/run_session.sh` pushes
  `session/<id>` and opens a pull request instead of merging and pushing `main`;
  `.github/workflows/session.yml` gains the permission and token the runner needs
  to do it.
- **Patch 2** — `core_change_requests/patches/2026-08-08-pr-mode-2-validate-workflow.diff`
  (verified with `git apply --check`). Adds
  `.github/workflows/session-validate.yml`, which runs the validator **read from
  the pull request's base ref** and reports a check named `validate-session`.

BL-0005's stated prerequisite is already satisfied on `main`: the runner pushes
before deleting the session branch (commit `494790e`). Nothing in these patches
touches a sealed component, `CORE_MANIFEST.json`, or `loop/validate_session.sh`,
and no test references the loop machinery, so the suite stays green — which
matters, because a red suite flips the next session into maintenance mode.

## Five things BL-0005 does not say, that the work surfaced

These change the design rather than decorate it. Items 1 and 4 are the ones that
would have deadlocked the loop.

### 1. The default `GITHUB_TOKEN` cannot satisfy the required check

BL-0005 §4 says to keep the default `GITHUB_TOKEN` so pull requests are authored
by `github-actions[bot]`, and its reasoning for that is sound: GitHub forbids a
pull request's author from supplying its own approving review, so a pull request
opened under the human's identity could never be approved by the human.

But GitHub also does not trigger workflows from events created with the default
`GITHUB_TOKEN` — the recursion guard. A session pull request opened with it gets
**no `pull_request` run at all**, so a required `validate-session` check sits
pending forever and the pull request can never merge. Both halves of §4 cannot
hold at once with that token.

Resolution, and the only combination that satisfies both constraints: open the
pull request with a **GitHub App installation token** (or a fine-grained PAT on a
dedicated machine account) carrying `contents: write` and `pull-requests: write`.
Events from those tokens do trigger workflows, and the author is still not the
human, so the approval requirement keeps its meaning.

Patch 1 wires this as `GH_TOKEN: ${{ secrets.SESSION_PR_TOKEN || secrets.GITHUB_TOKEN }}`.
The fallback keeps the runner working from the moment the patch lands; the secret
must exist **before** step 3 turns the check into a requirement.

### 2. `session.yml` lacks `pull-requests: write`

It grants `contents: write` only. `gh pr create` fails 403 without the second
permission. Patch 1 adds it.

### 3. The `GITHUB_TOKEN` fallback needs a repository setting

Settings → Actions → General → **"Allow GitHub Actions to create and approve pull
requests"** must be enabled, or `GITHUB_TOKEN` cannot open a pull request at all.
This applies only to the fallback path; with `SESSION_PR_TOKEN` set it is
irrelevant.

### 4. The salvage path still pushes `main` directly

`run_session.sh`'s failure branch commits the journal and handoff and runs
`git push origin main`. Under the step 3 ruleset that push is refused, and the
runner treats the refusal as fatal — so every failed session would strand its
journal off `main`. ADR-0008 exit criterion 2 requires precisely the opposite:
the journal and handoff reach `main` while the rejected work stays quarantined.

Patch 1 therefore converts the salvage to the same reviewed path: cut
`salvage/<id>` from `main`, commit the narrative artifacts there, push, and open
a pull request. `failed/<id>` still preserves the whole branch for forensics,
pushed before anything else happens.

### 5. The required check must not run the full validator on a salvage branch

A salvage branch exists *because* its session failed validation. Re-running the
validator against it guarantees a red check and permanently strands the journal.
So `session-validate.yml` classifies by head ref:

- `session/*` → the full validator, read from the base ref.
- `salvage/*` → a narrower check: the diff touches nothing but `journals/` and
  `HANDOFF.md`.
- anything else → passes with a note. Without this a required check would block
  every ordinary human pull request against `main`, including the ones that
  repair the loop.

## How to apply

```bash
git apply core_change_requests/patches/2026-08-08-pr-mode-1-runner.diff
git apply core_change_requests/patches/2026-08-08-pr-mode-2-validate-workflow.diff

bash -n loop/run_session.sh
python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"
python scripts/validate_repository.py
python -m unittest discover -s tests
```

Then, in order:

1. Merge the patched machinery to `main` (still under the current direct-push
   rules — the runner is not yet gated).
2. Create `SESSION_PR_TOKEN` (GitHub App installation token preferred).
3. Dispatch `session.yml` manually. Confirm it opens a session pull request and
   that `validate-session` reports on it. **Do not enable step 3 until a real
   pull request has shown a green check** — a required check that has never run
   is indistinguishable from one that cannot run.
4. Only then apply BL-0005 step 3 to the `main history protection` ruleset:
   require a pull request before merging (1 approval), require review from Code
   Owners, and require the status check named `validate-session`.
5. Delete the `Bash(git push origin main …)` enumeration from
   `.claude/settings.json`, as BL-0006 says to: once the server refuses every
   direct push to `main`, the enumeration is a guardrail pretending to be a
   boundary.

The ordering is not stylistic. Enabling step 3 against the current runner does
not gate sessions — it destroys them.

## Open questions for the human

- **Exit code on a failed session.** Preserved as-is: a successful salvage still
  exits 0, so a failed session shows green in Actions. The salvage pull request
  title says `FAILED validation`, so it is not invisible, but making the run red
  would be a louder signal. Deliberately left unchanged as out of BL-0005's
  scope.
- **Branch cleanup.** The runner no longer deletes session branches. Nothing
  prunes `session/*`, `salvage/*`, `failed/*` over time.
- **Merge cadence.** With this in place, an "unattended" session still needs a
  human to approve and merge. That is the intent of exit criterion 1 as written,
  but worth confirming it is the intent in practice before five sessions queue up
  waiting.

## What is blocked until this is applied

Counting toward ADR-0008 exit criterion 1. `HANDOFF.md` already says not to start
counting until BL-0005 lands, because until then a green validator is the session
vouching for itself and `CODEOWNERS` binds nothing. Manual `workflow_dispatch`
runs are not blocked and should happen first.
