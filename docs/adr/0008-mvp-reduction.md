# ADR-0008: MVP Reduction to the Smallest Provable Autonomous Loop

- Status: accepted, human-directed and human-supervised
- Date: 2026-08-08
- Change: supervised MVP reduction (no autonomous A-number consumed)
- Generation: G-0003 (unchanged)

## Context

The repository describes more capability than it has ever exercised. Nine core
skills, four capability documents, and a scheduled-task specification exist,
but no unattended session has ever run: there is no runner, no scheduler, no
session validator, and no external enforcement of the protections the
documents describe. Every session to date has been human-driven.

Carrying an unproven surface has a cost. Each additional skill and document is
orientation load for a fresh agent, an implied promise the system has not
kept, and a place for description to drift from behavior. The smallest
complete autonomous operating loop — wake, orient, do one unit of real work,
validate, hand off, stop — needs only a fraction of what is here.

This reduction was executed under direct human supervision. Nothing that has
ever served as evidence is destroyed. History is never rewritten. The full
pre-reduction state is preserved by the annotated tag `pre-mvp-freeze`, which
is the source of truth for every parked component.

## Decision

Reduce the working tree to the minimum required to prove the loop, then add
the missing loop machinery.

### Keep

- Evidence spine, untouched: `EXPERIMENTS.jsonl`, `FAILURES.md`,
  `DECISIONS.md`, `results/`, `reviews/`, `data/snapshots/`, `data/raw/`,
  `data/provenance/`.
- Sealed core, untouched: `evaluator/daily_bar.py`, `scripts/`, `schemas/`,
  `CORE_MANIFEST.json` sealed-component entries.
- Skills: `genesis-orchestrator`, `experiment-loop`, `memory-handoff`.
- Docs: `docs/evaluator-contract.md` and every file under `docs/adr/`.
- Canonical state and contracts: `MISSION.md`, `CONTEXT.md`, `STATE.json`,
  `HYPOTHESES.md`, `DATA_MANIFEST.json`, `README.md`, `data_adapters/`,
  `strategies/`, `tests/`, `logs/`.

### Park (retrievable from `pre-mvp-freeze`)

Docs, removed from the working tree with `git rm`:

- `docs/capability-map.md`
- `docs/scheduled-task-specification.md`
- `docs/source-evaluation.md`
- `docs/tooling-recommendations.md`

Skills, intended for parking but **blocked** — they remain in the working
tree:

- `skills/hypothesis-engine/`
- `skills/evidence-gate/`
- `skills/data-integrity/`
- `skills/paper-execution/`
- `skills/skill-lifecycle-governance/`
- `skills/anti-degradation-triage/`

The sealed validator `scripts/validate_repository.py` hardcodes all nine
skills in its internal `CORE_SKILLS` set and fails if any skill directory is
missing or if `CORE_MANIFEST.json`'s `core_skills` differs from that set.
Removing these skills therefore requires a sealed-generation change (G-0004),
which is out of scope for this reduction. The human supervising this
reduction reviewed the finding and directed that the six skills stay in place
until a G-0004 change proposal — which must also cover un-hardcoding the
skill set — is approved through the normal core-change process. Until then,
sessions must treat only `genesis-orchestrator`, `experiment-loop`, and
`memory-handoff` as operative; the other six are dormant and must not be
invoked.

### Delete (duplicates, no evidence value)

- `data/SPY_2024-01-02_2025-12-31_1day.csv`
- `data/SPY_2024-01-02_2026-08-05_1day.csv`

Both were verified byte-identical (SHA-256 match and `cmp`) to the
content-addressed snapshots `data/snapshots/D-0001/2255…ea30.csv` and
`data/snapshots/D-0002/711f…3f81.csv` before removal, and
`DATA_MANIFEST.json` resolves every dataset path to `data/snapshots/`. The
top-level copies only invited accidental use of a non-canonical path. The
snapshots remain; nothing is lost.

### Add

Loop machinery under `loop/`, `.github/workflows/session.yml`,
`.claude/settings.json`, and `CODEOWNERS`, plus a seeded `HANDOFF.md`,
`journals/`, and `backlog/`. The workflow ships with `workflow_dispatch`
only; the schedule trigger is enabled by a human after the first manual runs
succeed.

## Re-entry rule

A parked component returns only when all of the following hold:

1. A session is concretely blocked or degraded without it, and that blockage
   is recorded in `FAILURES.md` or a session journal — not merely
   anticipated.
2. A human restores it by pull request from the `pre-mvp-freeze` tag.
3. One component per pull request, so each return is individually justified.

Absence of a parked component is never an emergency. An agent that believes
it needs one records the blockage and stops; it does not restore anything
itself.

## Exit criteria for the loop proof

The reduction succeeds when all of the following have been demonstrated:

1. Five consecutive scheduled sessions run with no human input mid-run, each
   leaving a validated artifact and an updated handoff with
   `loop/validate_session.sh` green.
2. One deliberately induced validation failure salvages correctly: the
   journal and handoff reach `main` while the rejected work is quarantined to
   a `failed/` branch.
3. One forced maintenance-mode session produces a diagnosis rather than
   research.
4. One cold-start session from a fresh clone orients purely from repository
   state and does not redo completed work.
5. One full human-approval round trip completes: the agent files the
   evaluator validity-stamp change request, the human approves it, a sealed
   G-0004 lands, and the agent resumes under it.

## Enforcement reality

Added 2026-08-08 after an adversarial review of the branch-protection options.
This section exists because the rest of this ADR could otherwise be read as
claiming protection the repository does not have.

**Binding on everyone, enforced server-side by GitHub:**

- `main` cannot be force-pushed or deleted (ruleset `main history protection`,
  rules `deletion` + `non_fast_forward`, no bypass actors).
- Tags matching `pre-*` cannot be updated or deleted (ruleset
  `freeze tag immutability`, rules `update` + `deletion` + `non_fast_forward`,
  no bypass actors). This is what makes the sealed-hash check meaningful: the
  check reads `CORE_MANIFEST.json` from `pre-mvp-freeze`, and a movable tag
  would be a movable root of trust. Verified empirically by a rejected
  fast-forward tag move, which the `update` rule refuses and which
  `non_fast_forward` alone would have permitted.

**Self-policed, enforced only by code the session itself runs:**

- `loop/validate_session.sh`, invoked by `loop/run_session.sh` from `main`
  rather than from the branch under test, so a session that tampers with the
  validator does not get to judge itself.
- The `.claude/settings.json` deny rules and the runner's `--allowedTools`
  allowlist.

**Not in effect: `CODEOWNERS`.** It binds only through a required pull-request
review, which is deliberately disabled so the runner can push `main` directly.
Until the loop is pull-request-based (BL-0005), `CODEOWNERS` is a statement of
intent, not a control. Enabling "Require a pull request" before that change
would not gate sessions; it would destroy their output, because the runner
treats a rejected push as a warning.

Branch protection therefore bounds the irreversible failure — history rewriting
— while the reversible failure, a bad forward commit, is caught only by
machinery the agent could in principle reach. That asymmetry is accepted for
the MVP and closed by BL-0005.

**Amended 2026-08-09 by ADR-0009:** the asymmetry is permanent by decision,
not provisional. BL-0005 is rescinded — the agent owns forward motion; the
human owns the core. See `0009-agent-owned-operations.md` for the enforcement
layering that supersedes the paragraph above.

## Consequences

- The working tree now claims only what the loop can prove.
- Six skills remain physically present but dormant under the sealed-validator
  constraint; the mismatch between "kept" and "operative" is explicit here
  and in `HANDOFF.md` rather than silent.
- The first real test of the human-approval gate is already queued: the
  evaluator validity-stamp defect (stamps written as `"passed"`
  unconditionally) is documented, deliberately unfixed, and reserved for the
  G-0004 round trip.
- Every parked or deleted path remains retrievable from `pre-mvp-freeze`;
  recovery is a deliberate human act, not an agent convenience.
