# BL-0002: Draft the G-0004 core-change request (validity stamps)

- Status: DONE (2026-08-09, session `2026-08-09-0851`) — see "Outcome" below
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

## Outcome (2026-08-09, session `2026-08-09-0851`)

`core_change_requests/CCR-0001-g0004-validity-stamps.md` exists and covers all
seven points plus 6a. Nothing sealed or protected was modified; the validator
reports valid and the suite is 68 passed / 1 skipped / 187 subtests. The
request is **proposed**, awaiting human approval — the agent half of ADR-0008
exit criterion 5 is complete.

Mapping of the seven required points to the document: 1 → §1 and §1a; 2 → §2;
3 → §3.1–§3.5; 4 → §4; 5 → §5; 6 → §6; 6a → §6a; 7 → §7. The BL-0001
interpreter question is answered in §8.

Four things the drafting turned up that were not in this item's scope list:

1. **Honest stamps make promotion impossible** until B-0003 resolves.
   `scripts/finalize_experiment.py` (lines 116–120) blocks promotion unless
   all five checks read `"passed"`, and two of the five cannot honestly read
   `"passed"` on this data path (`survivorship_check` is `"not_applicable"`
   on a static one-symbol universe; `corporate_action_check` is `"not_run"`
   while the provider exposes no adjustment semantics). §3.6 states the three
   possible responses and recommends leaving the gate strict. This is the
   decision the human most needs to make, and it did not exist as a question
   before the request was written.
2. **A migration hazard that would wedge the loop.** `loop/validate_session.sh`
   check 5 verifies sealed hashes on the session branch against
   `CORE_MANIFEST.json` at `REFERENCE_TAG`. Between G-0004 landing on `main`
   and `REFERENCE_TAG` moving, every session fails validation through no fault
   of its own, and the agent cannot repair it — both paths are protected. §6a
   gives the required sequence.
3. **`tests/test_golden_replay_e0002.py` breaks under G-0004.** It loads the
   evaluator from the working tree and asserts its hash equals the G-0002
   sealed hash. It must be repointed at the historical bytes in the same
   change, or the replay silently stops being a replay of E-0002. §5.
4. **A real, small defect in the sealed evaluator.** Line 417 passes
   `strategy(dict(history), date)` — a shallow copy, so the strategy holds the
   evaluator's own row lists and mutable row dicts. It cannot see the future
   through them but it can rewrite the past mid-run. Folded into §3.1 as part
   of the lookahead invariant rather than raised separately, since G-0004 is
   the only generation bump on the table.

Deliberate omission: **no patch is attached**, unlike the earlier requests in
`core_change_requests/`. Those touched `loop/` and `.github/`; this one touches
the sealed evaluator and validator, where an agent-authored diff invites
review-by-skim of exactly the code the approval boundary exists to protect.
Reasoning and reversal conditions are in §9.
