# BL-0002: Draft the G-0004 core-change request (validity stamps)

- Status: **DONE (agent side) 2026-08-09** — see "Outcome 2026-08-09" below.
  The deliverable exists at
  `core_change_requests/CCR-0001-g0004-validity-stamps.md` and awaits human
  approval, which is exit criterion 5 and outside this item.
- Priority: 2
- Requires sealed changes: NO — this item drafts the request only
- Origin: ADR-0008 proof backlog (2026-08-08)

## The defect

`evaluator/daily_bar.py` (sealed under CORE_MANIFEST component EV-0002)
writes five validity stamps unconditionally as `"passed"` when finalizing an
experiment — see the `validity = {**prereg["validity"], ...}` block around
lines 429–437: `lookahead_check`, `survivorship_check`, `leakage_check`,
`corporate_action_check`, `missing_data_check`. No corresponding check is
performed. Both completed experiments (E-0001, E-0002) carry these
unearned stamps in `results/*/validity.json` and `EXPERIMENTS.jsonl`.

This defect is known, deliberate to leave in place, and reserved as the first
test of the human-approval gate operating inside the proved loop (ADR-0008
exit criterion 5). Do NOT fix it. Do NOT touch the evaluator, its manifest
hash, or any existing evidence.

## Deliverable

`core_change_requests/CCR-0001-g0004-validity-stamps.md` containing, per the
ADR-0007 approval-boundary requirements:

1. Each sealed/protected file requiring change — at minimum
   `evaluator/daily_bar.py` and the corresponding `CORE_MANIFEST.json`
   sealed-component hash entries; state whether
   `scripts/validate_repository.py` also changes (it validates the
   `VALIDITY_FIELDS` set, and per ADR-0008 its hardcoded `CORE_SKILLS` set
   also needs un-hardcoding in the same generation — include that in scope
   or argue explicitly for deferring it).
2. The exact non-bypassable invariant each change adds — e.g. a stamp may
   only be `"passed"` if a named, logged check ran; otherwise `"not_run"` or
   `"failed"`.
3. What each of the five checks would actually verify for a daily-bar,
   single-instrument, snapshot-fed evaluation, and which of them cannot be
   meaningfully implemented yet (e.g. survivorship on a one-symbol universe)
   and should honestly report `"not_run"`.
4. Migration and comparability: existing G-0002/G-0003 artifacts keep their
   recorded stamps unchanged (evidence is never rewritten); cross-generation
   results are not directly comparable per CORE_MANIFEST change_policy.
5. Tests that fail under the current behavior (a run whose stamps say
   "passed" with no check log must fail under G-0004).
6. Rollback and historical-artifact preservation behavior.
6a. The successor freeze tag. `loop/validate_session.sh` verifies sealed
   hashes against `CORE_MANIFEST.json` as it exists at `REFERENCE_TAG`
   (a variable at the top of that script), currently `pre-mvp-freeze`. A
   G-0004 that changes sealed hashes therefore needs a new reference tag and
   a one-line change to that variable. Do **not** move `pre-mvp-freeze` — it
   is immutable by ruleset and is the historical record.

   Constraint the request must state explicitly: the tag ruleset
   `freeze tag immutability` matches `refs/tags/pre-*`. A successor named
   outside that pattern (`g0004-freeze`, say) would be created successfully
   and protected by nothing, with no error at any point. Name it
   `pre-g0004-freeze` or equivalent, or add a second include pattern to the
   ruleset first — and verify with a rejected force-update before relying on
   it, the same way `pre-mvp-freeze` was verified.
7. The explicit human approval point: what the human must approve, and that
   the agent stops there.

## Input from BL-0001 (2026-08-09), to weigh not to assume

The golden replay found that `metrics.json` is not bit-reproducible across
CPython minor versions: `turnover` is the one metric computed through `sum()`
over a long float list, and 3.12 changed that to compensated summation. E-0002
was recorded on >= 3.12; the loop runner pins 3.11. `design.environment_id` is
free text (`"python-stdlib-mvp"`) and no interpreter version is recorded or
enforced anywhere. See the "Outcome 2026-08-09" section of
`backlog/BL-0001-golden-replay-e0002.md` for the evidence.

Decide, when drafting the request, whether pinning/recording the interpreter
belongs in the G-0004 scope or is a separate smaller change. Argue it either
way, but do not leave it unmentioned.

## Definition of done

The request document exists, is complete per the list above, is referenced
from the journal and HANDOFF.md, and nothing sealed was touched. A human
approving it (and the subsequent sealed G-0004 landing) is exit criterion 5
and happens outside this item.

## Outcome 2026-08-09 (session `2026-08-09-0800`)

`core_change_requests/CCR-0001-g0004-validity-stamps.md` is filed. All seven
points plus 6a and the BL-0001 input are covered; `scripts/validate_repository.py`
reports valid and `git status` shows no sealed, protected, or evidence path
touched.

Four things the drafting found that this item did not anticipate, recorded here
so they are not rediscovered:

1. **`scripts/finalize_experiment.py` had to be added to scope.** Its
   `PROMOTION_CHECKS` (lines 13–19) already refuses promotion unless all five
   stamps equal `"passed"` (lines 116–120). The gate is not missing — the
   evaluator is forging its input. Fixing only the evaluator would turn a fake
   pass into a permanent deadlock, because an honest `"not_applicable"` (which
   survivorship on a one-symbol universe must return) is not `"passed"`.
2. **The minimum honest fix is a deletion.** The preregistered validity values
   are all `"not_run"` (`scripts/preregister_experiment.py` lines 149–153) and
   the evaluator builds `{**prereg["validity"], <five overrides>}`. Removing the
   five override lines alone yields honest stamps. Everything beyond that exists
   to let a check that *does* run say so credibly.
3. **`schemas/experiment.schema.json` needs no change** and was argued out of
   scope: `$defs.check` already admits `not_run`/`not_applicable`/`failed`/
   `warning`, and the validator's `VALIDITY_FIELDS` is a key-presence check, not
   a value check. The schema returns to scope only if the human wants the check
   record inside `validity.json` instead of a separate `checks.json`.
4. **`tests/test_golden_replay_e0002.py` breaks under G-0004 by construction**,
   at two named assertions (lines 188 and 221). BL-0001's own deliverable is a
   migration cost of this item's deliverable. The request specifies the rewrite
   — replay against the G-0002 evaluator bytes read from git rather than the
   on-disk file — as part of the same landing.

The interpreter-version question routed here by BL-0001 is **decided in the
request, section 8**: record it in `design.environment_id`, do not enforce it,
include the recording in G-0004's scope because
`scripts/preregister_experiment.py` is sealed under the same component. The
counter-argument (require an enforced environment digest instead) is stated
fairly and left for the human to take up.
