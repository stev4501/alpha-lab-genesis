# Handoff

Rewritten 2026-08-09 by autonomous session `2026-08-09-0851` (research mode).
Every autonomous session rewrites this file completely, except the
"Exit criteria" section, which persists with updated progress notes.

## Current state (three sentences)

The repository is healthy — `scripts/validate_repository.py` reports valid and
`python -m pytest tests -q` is 68 passed / 1 skipped / 187 subtests — and the
loop is still in its loop-proving phase, so research remains frozen: no new
strategy experiments, no hypothesis registration, no holdout access. Session
2026-08-09-0851 closed BL-0002 by writing
`core_change_requests/CCR-0001-g0004-validity-stamps.md`, the request that asks
a human to approve a sealed G-0004 in which the five validity stamps stop being
string literals and become derived from a check ledger the evaluator writes as
`results/<E>/checks.json`; nothing sealed or protected was touched and the
request is **proposed**, not applied. That completes the agent half of exit
criterion 5 — the human half (approve, land G-0004, resume under it) is now the
only thing in this repository waiting on a person.

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
  BL-0001 and BL-0002 are DONE; BL-0005 is RESCINDED (ADR-0009); BL-0006 is
  CLOSED. Open: **BL-0003 (3), BL-0004 (4)** — both documentation units, both
  independent of the pending human approval.
- Pending human approval: `core_change_requests/CCR-0001-g0004-validity-stamps.md`.
  Read it before touching anything near the evaluator, the validator, or the
  validity stamps — it is the current proposal of record for all three, and
  §6a describes a migration ordering that can wedge the loop if it is landed
  wrong.
- Operative skills: `genesis-orchestrator`, `experiment-loop`,
  `memory-handoff`. Six other skills are physically present but dormant
  pending the G-0004 change (see ADR-0008); do not invoke them.
- Known, deliberately unfixed defect: `evaluator/daily_bar.py` writes the five
  validity stamps as `"passed"` unconditionally (lines 429–437). It stays
  unfixed until a human lands G-0004. Leave it alone. CCR-0001 is the request;
  the defect itself is untouched on `main`.
- Second known defect, now documented and also unfixed: line 417 passes
  `strategy(dict(history), date)` — a shallow copy, so a strategy can mutate
  the evaluator's own bar history mid-run. Folded into CCR-0001 §3.1. Also
  leave it alone.

## Exact next action

Take **BL-0003** (`backlog/BL-0003-b0003-provider-evidence.md`), now the
highest-priority open item, and produce the analysis document (suggested path
`docs/b0003-provider-evidence.md`) enumerating what a data provider would have
to expose for point-in-time status to be *verifiable* rather than asserted —
the six elements listed in that file, each with what today's provider exposes,
what it would let us machine-enforce, and which future check would consume it.

Two inputs that did not exist when BL-0003 was written:

1. CCR-0001 §3.4 states that `corporate_action_check` must read `"not_run"`
   under G-0004 and stay there until this blocker resolves. BL-0003's element
   5 (adjustment semantics) is therefore the direct input to a named check —
   say so concretely rather than in the abstract.
2. CCR-0001 §3.5 proposes an optional `expected_sessions` field in
   `DATA_MANIFEST.json` as the only way `missing_data_check` can honestly
   pass. That is a declared-expectation mechanism, and BL-0003 should say
   whether the same pattern helps or hurts for the point-in-time elements —
   a human-registered number is assurance about the registration, not about
   the provider.

Do not start a second unit. If BL-0003 is finished with time left, spend it on
journal quality, not on BL-0004.

Do **not** attempt any part of G-0004 itself: it requires sealed changes, it is
awaiting human approval, and every path it touches is denied to the agent.

## Open questions

1. ~~**Should the interpreter version be part of the experiment contract?**~~
   Answered in CCR-0001 §8, as a recommendation awaiting approval: **record**
   the interpreter version in G-0004 (two lines, no new invariant), **do not
   enforce** it yet (enforcement changes the meaning of
   `design.environment_id`, reaches `scripts/preregister_experiment.py`, and
   deserves its own request). The counter-argument is preserved in §8; the
   human decides.
2. **Is `STATE.json` supposed to track the loop-proving phase at all?** Its
   `run` block still describes a completed run from 2026-08-06 and its
   `next_actions` are frozen research. No autonomous session has updated it,
   and no rule says one should. Unchanged from the last handoff, but now with
   a deadline attached: CCR-0001 §4 notes that landing G-0004 requires
   `STATE.json.objective.system_generation` to move to `G-0004`, so this
   should be answered *before* that migration, not during it.
3. **New — the biggest question CCR-0001 raises:** honest validity stamps make
   promotion impossible until B-0003 resolves.
   `scripts/finalize_experiment.py` (lines 116–120) blocks promotion unless
   all five checks read `"passed"`, and two of them cannot honestly do so on
   this data path. §3.6 lays out three responses and recommends the strict
   one. Nothing has ever been promoted (`champion_strategy_id: null`), so
   nothing is lost today — but this is the decision the human most needs to
   make, and it is not a decision any session can make for them.

## Time-sensitive

Nothing is expiring. One thing is *sequencing*-sensitive rather than
time-sensitive, and it is worth knowing before it bites:

If and when G-0004 lands, `loop/validate_session.sh`'s `REFERENCE_TAG` must
move to the successor freeze tag in the same window. Check 5 verifies sealed
hashes on the session branch against `CORE_MANIFEST.json` *at the reference
tag*; between the new evaluator reaching `main` and the tag moving, every
session fails validation for a reason unrelated to its work and is quarantined
to `failed/`. Both paths are protected, so no session can repair it. CCR-0001
§6a gives the required order and the tag-naming trap (the ruleset matches
`refs/tags/pre-*`; a tag named outside that pattern is created successfully and
protected by nothing, with no error anywhere). A session that fails inside that
window is not evidence about the loop and must not be counted against exit
criterion 1.

## Exit criteria (persistent — update progress notes only)

The loop is proved when all five have been demonstrated:

1. Five consecutive scheduled sessions with no human input mid-run, each
   leaving a validated artifact and an updated handoff with
   `loop/validate_session.sh` green. — progress: 2/5 pending validation.
   `2026-08-09-0525` and `2026-08-09-0851` each produced work; whether they
   count depends on the runner's validator passing, which a session cannot
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
   the agent resumes under it. — **agent half complete** (2026-08-09-0851):
   `core_change_requests/CCR-0001-g0004-validity-stamps.md` is filed and
   proposed. Awaiting a human decision on §7's seven approval points; the
   remaining three quarters of this criterion (approve, land, resume) cannot
   be advanced by any session.
