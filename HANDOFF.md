# Handoff

Written 2026-08-08 by the human-supervised MVP reduction session (ADR-0008).
Every autonomous session rewrites this file completely, except the
"Exit criteria" section, which persists with updated progress notes.

## Current state (three sentences)

The repository was reduced to the minimum surface needed to prove the
autonomous loop (ADR-0008): four capability docs parked to the
`pre-mvp-freeze` tag, two duplicate data CSVs deleted after byte-identity
verification, and the loop machinery (`loop/`, `.github/workflows/session.yml`,
`.claude/settings.json`, `CODEOWNERS`) added with `workflow_dispatch` only.
No autonomous session has ever run; you may be the first — the loop itself is
what is being proved, and the backlog below is the only sanctioned work.
Research is frozen: no new strategy experiments, no hypothesis registration,
no holdout access until the exit criteria are met and a human re-opens
research.

## Orientation for a fresh agent

- Mission and constraints: `MISSION.md`, `CONTEXT.md`, ADRs under `docs/adr/`
  (read `0008-mvp-reduction.md` and `0009-agent-owned-operations.md` first —
  0009 settles who owns what: the agent owns forward motion, the human owns
  the sealed core and its approvals).
- Machine state: `STATE.json` (schema: `schemas/state.schema.json`).
- Evidence: `EXPERIMENTS.jsonl` (append-only), `results/`, `reviews/`,
  `FAILURES.md` (open blockers B-0001, B-0003).
- Work queue: `backlog/` — one item per file, priority order in the filename.
- Operative skills: `genesis-orchestrator`, `experiment-loop`,
  `memory-handoff`. Six other skills are physically present but dormant
  pending the G-0004 change (see ADR-0008); do not invoke them.
- Known, deliberately unfixed defect: `evaluator/daily_bar.py` writes the five
  validity stamps (`lookahead_check`, `survivorship_check`, `leakage_check`,
  `corporate_action_check`, `missing_data_check`) as `"passed"`
  unconditionally. It is reserved as the first test of the human-approval
  gate (backlog item BL-0002). Leave it alone.

## Exact next action

Take the highest-priority open item in `backlog/` (currently
`BL-0001-golden-replay-e0002.md`) and advance it per its own instructions.
One unit of work per session.

## Open questions

- None yet from an autonomous session. The first sessions should surface
  theirs here.

## Exit criteria (persistent — update progress notes only)

The loop is proved when all five have been demonstrated:

1. Five consecutive scheduled sessions with no human input mid-run, each
   leaving a validated artifact and an updated handoff with
   `loop/validate_session.sh` green. — progress: 0/5. Counting starts with
   the first scheduled session after the ADR-0009 revert lands: the loop is
   deliberately direct-push (BL-0005 rescinded), a green validator
   self-vouching is the intended evidence here, and the damage a wrong
   session can do is bounded by server-side history protection, not by a
   merge gate (ADR-0009, "Enforcement, honestly, by layer").
2. One deliberately induced validation failure that salvages correctly:
   journal and handoff reach `main`, rejected work quarantined to a
   `failed/` branch. — not attempted
3. One forced maintenance-mode session that produces a diagnosis rather than
   research. — not attempted
4. One cold-start session from a fresh clone that orients purely from
   repository state and does not redo completed work. — not attempted
5. One full human-approval round trip: the agent files the validity-stamp
   change request (BL-0002), the human approves, a sealed G-0004 lands, and
   the agent resumes under it. — not attempted
