# BL-0002: Draft the G-0004 core-change request (validity stamps)

- Status: open
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
7. The explicit human approval point: what the human must approve, and that
   the agent stops there.

## Definition of done

The request document exists, is complete per the list above, is referenced
from the journal and HANDOFF.md, and nothing sealed was touched. A human
approving it (and the subsequent sealed G-0004 landing) is exit criterion 5
and happens outside this item.
