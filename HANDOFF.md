# Handoff

Rewritten 2026-08-09 by autonomous session `2026-08-09-0525` (research mode).
Every autonomous session rewrites this file completely, except the
"Exit criteria" section, which persists with updated progress notes.

## Current state (three sentences)

The repository is healthy — `scripts/validate_repository.py` reports valid and
`python -m pytest tests -q` is 50 passed / 112 subtests — and the loop is still
in its loop-proving phase, so research remains frozen: no new strategy
experiments, no hypothesis registration, no holdout access. Session
2026-08-09-0525 closed BL-0001 by adding `tests/test_golden_replay_e0002.py`,
which re-runs the sealed EV-0002 evaluator over E-0002's preregistered inputs in
a scratch root and shows that `equity.csv`, `trades.csv`, and `validity.json`
reproduce byte-for-byte while `metrics.json` differs in exactly one field
(`turnover`, last two digits) for a proven reason: CPython 3.12 changed `sum()`
over floats to compensated summation, E-0002 was recorded on >= 3.12, and the
loop runner pins 3.11. That finding is routed into BL-0002's scope as an input
to weigh; nothing sealed was touched and no recorded evidence changed.

## Orientation for a fresh agent

- Mission and constraints: `MISSION.md`, `CONTEXT.md`, ADRs under `docs/adr/`
  (read `0008-mvp-reduction.md` and `0009-agent-owned-operations.md` first —
  0009 settles who owns what: the agent owns forward motion, the human owns
  the sealed core and its approvals).
- Machine state: `STATE.json` (schema: `schemas/state.schema.json`). It is
  stale relative to the loop-proving phase — its `next_actions` (A-0009,
  A-0008) describe research work that is frozen. `backlog/` is the live queue.
- Evidence: `EXPERIMENTS.jsonl` (append-only), `results/`, `reviews/`,
  `FAILURES.md` (open blockers B-0001, B-0003, both owned by the dormant
  `data-integrity` skill).
- Work queue: `backlog/` — one item per file, priority order in the filename.
  BL-0001 is now DONE; BL-0005 is RESCINDED (ADR-0009). Open: BL-0002 (2),
  BL-0003 (3), BL-0004 (4), BL-0006 (6).
- Operative skills: `genesis-orchestrator`, `experiment-loop`,
  `memory-handoff`. Six other skills are physically present but dormant
  pending the G-0004 change (see ADR-0008); do not invoke them.
- Known, deliberately unfixed defect: `evaluator/daily_bar.py` writes the five
  validity stamps (`lookahead_check`, `survivorship_check`, `leakage_check`,
  `corporate_action_check`, `missing_data_check`) as `"passed"`
  unconditionally. It is reserved as the first test of the human-approval
  gate (backlog item BL-0002). Leave it alone.

## Exact next action

Take **BL-0002** (`backlog/BL-0002-g0004-change-request.md`), now the
highest-priority open item, and produce
`core_change_requests/CCR-0001-g0004-validity-stamps.md` per the seven-point
list in that file. It is a drafting task: write the request, touch nothing
sealed, and stop at the human approval point. Read the "Input from BL-0001
(2026-08-09)" section added to that file — you must decide, and argue either
way in the request, whether recording/pinning the interpreter version belongs
in the G-0004 scope.

Do not start a second unit. If BL-0002 is finished with time left, spend it on
journal quality, not on BL-0003.

## Open questions

1. **Should the interpreter version be part of the experiment contract?**
   `design.environment_id` is the free-text string `"python-stdlib-mvp"`.
   Nothing records or enforces a CPython version, and E-0002's `turnover`
   demonstrably depends on it. Answering this belongs to BL-0002's drafting.
2. **Is `STATE.json` supposed to track the loop-proving phase at all?** Its
   `run` block still describes a completed run from 2026-08-06 and its
   `next_actions` are frozen research. No autonomous session has updated it,
   and no rule says one should. Someone should decide deliberately whether
   sessions maintain it or whether `backlog/` + `HANDOFF.md` are the state of
   record during loop-proving; until decided, sessions have been leaving it
   alone, which is the safe default.
3. **BL-0006's scoping decision (options 1-3) is still open** and unaffected by
   anything this session did.

## Time-sensitive

Nothing. The 2026-08-09-0505 failure (unfunded `ANTHROPIC_API_KEY`; the agent
died 311 ms in, before producing a token) is resolved — this session ran to
completion on the same workflow, which is the evidence that credits exist. That
branch, `failed/2026-08-09-0505`, contains no work and needs no salvage. Do not
treat it as maintenance input.

## Exit criteria (persistent — update progress notes only)

The loop is proved when all five have been demonstrated:

1. Five consecutive scheduled sessions with no human input mid-run, each
   leaving a validated artifact and an updated handoff with
   `loop/validate_session.sh` green. — progress: 1/5 pending validation.
   `2026-08-09-0525` is the first session to produce work; whether it counts
   depends on the runner's validator passing, which the session cannot
   self-certify. `2026-08-09-0505` does not count — it never produced a token
   (API credits), so it is not evidence about the loop either way. Counting
   starts with the first scheduled session after the ADR-0009 revert landed
   (`0cbb3e2`): the loop is deliberately direct-push (BL-0005 rescinded), a
   green validator self-vouching is the intended evidence here, and the damage
   a wrong session can do is bounded by server-side history protection, not by
   a merge gate (ADR-0009, "Enforcement, honestly, by layer").
2. One deliberately induced validation failure that salvages correctly:
   journal and handoff reach `main`, rejected work quarantined to a
   `failed/` branch. — not attempted. Note: the salvage *path* has now run
   once for real (`33b0b1c`, session 0505) and did put a note on `main`, but
   the failure was not induced and there was no work to quarantine, so it does
   not demonstrate this criterion.
3. One forced maintenance-mode session that produces a diagnosis rather than
   research. — not attempted
4. One cold-start session from a fresh clone that orients purely from
   repository state and does not redo completed work. — not attempted
5. One full human-approval round trip: the agent files the validity-stamp
   change request (BL-0002), the human approves, a sealed G-0004 lands, and
   the agent resumes under it. — not attempted; the agent-side half is the
   next action above.
