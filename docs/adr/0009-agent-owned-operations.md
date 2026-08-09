# ADR-0009: Agent-owned operations, human-owned core

- Status: accepted, human-directed and human-supervised
- Date: 2026-08-09
- Change: supervised governance decision (no autonomous A-number consumed)
- Generation: G-0003 (unchanged)
- Amends: ADR-0008 ("Enforcement reality"); rescinds backlog item BL-0005 and
  the applied change from `core_change_requests/2026-08-08-pr-mode-loop.md`

## Context

ADR-0008 described the loop's enforcement posture as a temporary asymmetry:
server-side rules bound the irreversible failure (history rewriting), while a
bad forward commit is caught only by machinery the session itself runs.
BL-0005 was queued to close that asymmetry by making the loop
pull-request-based — every session's output waiting on a required check and a
human approval — and its steps 1 and 2 were drafted, then applied to `main`
(PR #5, commit `8906f4f`).

Two things then surfaced in the same supervised session. First, an
adversarial review of BL-0005's credential options showed that every workable
design either handed the session a repository-write credential anyway or
inserted a human approval into every session. Second, reviewing how
yoyo-evolve — the project that inspired this experiment — handles the same
problem made the actual intent explicit, and the human operator confirmed it
directly:

**The agent is meant to own this repository's forward motion.** A loop that
queues behind a human approval for every session is not unattended, and an
unattended loop is the thing being proved. The experiment is whether a
bounded agent, alone with the repository as its only memory, can do real
research work with no human in its operating loop — while the scientific
spine that makes the work believable stays in human hands.

## Decision

Ownership is split by kind of change, not by degree of supervision.

**The agent owns operations.** Sessions merge their validated work and push
`main` directly, as the pre-PR-#5 runner did. There is no pull-request gate,
no required status check, and no human approval on ordinary session output.
The default `GITHUB_TOKEN` with `contents: write` is sufficient; no
additional credential — machine account, PAT, or GitHub App — is created for
the loop, and none of the session's write ability outlives the job that
holds it.

**The human owns the core.** Sealed components (`evaluator/`, `scripts/`,
`schemas/`, `CORE_MANIFEST.json`), the loop machinery and protections
(`loop/`, `.github/`, `.claude/`, `CODEOWNERS`, `MISSION.md`, `CONTEXT.md`),
generation changes (G-XXXX), and freeze tags move only by human hands after
explicit approval. The G-0004 validity-stamp round trip (ADR-0008 exit
criterion 5) stands unchanged: the agent files the request and stops; the
human approves and applies.

## Enforcement, honestly, by layer

This supersedes the closing paragraph of ADR-0008's "Enforcement reality".

**Server-side, binding on everyone:** `main` cannot be force-pushed or
deleted; tags matching `pre-*` cannot be moved or deleted. These bound the
irreversible failure and anchor the sealed-hash root of trust. They stay.

**Runner-side, binding on the unattended agent:** the `--allowedTools`
allowlist, the deny rules in `loop/agent-settings.json`, and the validator
executed from `main`'s copy rather than the branch under test. These are the
operating gate for session output, and they are self-policed in ADR-0008's
sense: code the session's runner executes. That is no longer an accepted MVP
deficiency awaiting closure. It is the design.

**Amended 2026-08-09 (BL-0006).** Those deny rules were originally written in
`.claude/settings.json`, which is project-wide: it bound every Claude Code
session opened in this repository, supervised ones included, so the supervised
path for repairing the loop was strictly more awkward than the unsupervised
path for running it. The operator scoped them to the runner.
`.claude/settings.json` now keeps only what should bind every session
regardless of who is watching — evidence immutability and the `main`/history
guardrails — and `loop/run_session.sh` passes the core-ownership rules to the
unattended agent with `--settings`, refusing to start if that file is missing
or does not parse. Who owns the core did not change; the layer that expresses
it did. See `journals/2026-08-09-deny-rule-scoping.md`.

**Convention, binding on nobody:** `CODEOWNERS` remains a statement of
intent, permanently, since no required-review setting will ever activate it.
Human ownership of the core is real, but it is enforced by the layers above
plus the human being the repository's only admin — not by GitHub review
mechanics.

## Accepted risks, permanent

Named here so they are chosen rather than discovered:

1. **A bad forward commit is caught only by machinery the session runs.**
   A session that defeats its own validator can land tampered work on `main`.
   History protection guarantees the tampering is visible and reversible in
   history, and the append-only/immutability checks make it detectable by the
   next session or human review — but nothing server-side prevents it. This
   is the yoyo-evolve trade, taken with eyes open.
2. **The session's environment is readable by agent-executed code.**
   `ANTHROPIC_API_KEY` (and the job's `GITHUB_TOKEN`) are reachable from
   Python the agent writes, in a public repository whose logs and artifacts
   are world-readable. Bounded by `MAX_BUDGET_USD`, spend caps on the key
   itself, and the token's expiry with the job. Key rotation is the
   operator's lever if exfiltration is ever suspected.

## Rescission and rollback (human applies)

The applied BL-0005 change is reverted — the PR-mode runner solved a problem
this decision defines out of existence:

```bash
git revert --no-edit 8906f4f
# or, equivalently, the verified reverse diff:
git apply core_change_requests/patches/2026-08-09-rescind-pr-mode.diff
bash -n loop/run_session.sh
python scripts/validate_repository.py
python -m unittest discover -s tests
```

This restores the direct-push runner, removes
`.github/workflows/session-validate.yml`, and drops the `SESSION_PR_TOKEN`
wiring and `pull-requests: write` permission from `session.yml`.

Also undo, if they were done: delete the `SESSION_PR_TOKEN` secret; remove
any "require a pull request" / required-status-check additions to the
`main history protection` ruleset (the base deletion + non-fast-forward rules
stay). The `.claude/settings.json` push-deny enumeration stays as-is — the
server-side push boundary BL-0006 anticipated is now never coming, so the
guardrail keeps its job (see the note appended to BL-0006).

## Consequences

- Exit criterion 1 counting starts with the first scheduled session after the
  revert lands — the "wait for BL-0005" condition in `HANDOFF.md` is removed.
- BL-0005 is rescinded, its change request withdrawn; the drafted and revert
  patches are retained under `core_change_requests/patches/` as the record.
- No new credential exists to rotate, leak, or expire.
- The unattended path to first run shortens to: revert, dispatch
  `session.yml` manually, then enable the schedule.
- Worth queueing separately if sessions prove flaky, not queued now:
  yoyo-evolve's retry-with-shared-deadline pattern (multiple attempts inside
  one job, each budget clamped to a common wall-clock limit).
