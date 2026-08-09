# Handoff

Rewritten 2026-08-09 by autonomous session `2026-08-09-0800` (research mode).
Every autonomous session rewrites this file completely, except the
"Exit criteria" section, which persists with updated progress notes.

## Current state (three sentences)

The repository is healthy — `scripts/validate_repository.py` reports valid and
`python -m pytest tests -q` is 47 passed / 112 subtests — and the loop is still
in its loop-proving phase, so research remains frozen: no new strategy
experiments, no hypothesis registration, no holdout access. Session
2026-08-09-0800 closed BL-0002 on the agent side by filing
`core_change_requests/CCR-0001-g0004-validity-stamps.md`, the G-0004 request to
make the five validity stamps earned instead of hardcoded; it now awaits human
approval, which is exit criterion 5 and is not the agent's to perform. Nothing
sealed, protected, or evidential was touched, and no second unit was started.

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
  BL-0001 and BL-0002 are DONE; BL-0005 is RESCINDED (ADR-0009). Open:
  BL-0003 (3), BL-0004 (4), BL-0006 (6).
- Change requests: `core_change_requests/`. `CCR-0001-g0004-validity-stamps.md`
  is the only one awaiting approval; the other three are applied, withdrawn, or
  historical.
- Operative skills: `genesis-orchestrator`, `experiment-loop`,
  `memory-handoff`. Six other skills are physically present but dormant
  pending the G-0004 change (see ADR-0008); do not invoke them.
- Known, deliberately unfixed defect: `evaluator/daily_bar.py` writes the five
  validity stamps as `"passed"` unconditionally (lines 429–437). It is reserved
  as the first test of the human-approval gate. **Leave it alone** — the
  request describing its fix is now filed, and filing it does not authorize
  applying it.

## Exact next action

Take **BL-0003** (`backlog/BL-0003-b0003-provider-evidence.md`), now the
highest-priority open item: write `docs/b0003-provider-evidence.md` enumerating
what a data provider would have to expose for point-in-time status to be
verifiable rather than asserted, per the six elements in that file, and append
(do not edit) an updated "Resolution or next action" note to B-0003 in
`FAILURES.md`.

Read CCR-0001 section 3.5 first. It gives BL-0003 a concrete consumer it did not
have: `corporate_action_check` is the G-0004 check that would consume BL-0003's
elements 3 (revision identifiers) and 5 (adjustment semantics), and under the
proposed promotion gate that check sitting at `"not_run"` is one of the two
things that would block every promotion. BL-0003's element 6 ("what minimum
subset makes B-0003 closable") should be answered against that specific
consumer rather than in the abstract.

Do not start a second unit. Do not retrieve data. Do not change any dataset's
status.

## Open questions

1. **Should promotion be permanently blocked while checks are honestly
   `not_run`?** CCR-0001 §2.4 says yes and declines to propose a waiver, on the
   grounds that the first use of a waiver would be to paper over the very gap it
   exists to record. It costs nothing today (research frozen, no promotion
   pending) and could cost everything later. This is the single most consequential
   judgment in the request and the human should engage it directly.
2. **Should `survivorship_check` return `not_applicable` or `not_run`** on a
   one-symbol static universe? CCR-0001 §3.3 chose `not_applicable`, which under
   §2.4's accept-set is the difference between promotable and not. It is the one
   verdict in that request's table that is a judgment call rather than a fact.
3. **Interpreter version: recorded, not enforced.** CCR-0001 §8 decides this
   (record it in `design.environment_id`, include in G-0004 scope because
   `scripts/preregister_experiment.py` is sealed under the same component) and
   states the counter-argument — require an enforced environment digest instead —
   fairly. Open question 1 from the previous handoff is therefore answered, not
   still open; what remains is whether the human agrees.
4. **Is `STATE.json` supposed to track the loop-proving phase at all?** Carried
   forward unchanged. Its `run` block still describes a completed run from
   2026-08-06 and its `next_actions` are frozen research. No autonomous session
   has updated it and no rule says one should; sessions have been leaving it
   alone, which is the safe default. Note that A-0008's description ("prepare the
   narrow G-0004 change proposal") is the ancestor of CCR-0001, but A-0008 is
   owned by a dormant skill and its prerequisite is unmet — CCR-0001 was filed
   under BL-0002's authority and is deliberately narrower.
5. **BL-0006's scoping decision (options 1–3) is still open** and unaffected by
   anything this session did.

## Time-sensitive

Nothing is time-sensitive. Two things are worth knowing before they are
misread:

- The test count moved from 50 to 47 between the previous handoff and this one.
  Nothing broke: supervised commit `260e88f` (2026-08-09 07:04 UTC) reverted the
  `enabledPlugins` declaration after a cloud probe disproved it and removed the
  three tests that asserted it. The subtest count is unchanged at 112.
- If and when a human applies G-0004, expect `loop/validate_session.sh` to fail
  in the window between resealing the hashes and creating the successor freeze
  tag. That failure is correct. **Do not resolve it by editing hashes** — see
  CCR-0001 §6a, which also explains why the successor tag must be named
  `pre-g0004-freeze` (the ruleset pattern is `refs/tags/pre-*`; a tag named
  outside it is created successfully, protected by nothing, and errors nowhere).

## Exit criteria (persistent — update progress notes only)

The loop is proved when all five have been demonstrated:

1. Five consecutive scheduled sessions with no human input mid-run, each
   leaving a validated artifact and an updated handoff with
   `loop/validate_session.sh` green. — progress: 2/5 pending validation.
   `2026-08-09-0525` and `2026-08-09-0800` each produced work; whether they
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
   the agent resumes under it. — **agent-side half complete 2026-08-09**:
   `core_change_requests/CCR-0001-g0004-validity-stamps.md` is filed and
   BL-0002 is closed. The remaining three quarters (approve, land, resume) are
   human-gated and cannot be advanced by any session until the human acts. No
   autonomous session should treat the filing as permission to implement.
