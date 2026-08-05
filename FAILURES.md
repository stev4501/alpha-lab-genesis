# Failures and Blockers

Retain failures because discarded evidence constrains future search.

## Open

None.

## Resolved

### B-0002: Benchmark clock differs from strategy clock

- First observed: `E-0001`
- Classification: evaluator contract mismatch
- Impact: blocks interpretation of net excess return
- Evidence: strategy enters on the second session open; benchmark begins on the first session open
- Attempts: `EV-0001` retained unchanged; no in-generation patch was made
- Resolution: `EV-0002` under `G-0002` aligns benchmark and strategy at the evaluation start
- Owner: `skill-lifecycle-governance`

### B-0001: No validated point-in-time dataset

- First observed: genesis
- Impact: resolved; previously blocked valid strategy experiments
- Evidence: `DATA_MANIFEST.json` contains no validated dataset
- Resolution: `D-0001` registered and validated for price-return evaluation
- Owner: `data-integrity`

## Failure Entry Template

```markdown
### <ID>: <title>

- First observed:
- Last observed:
- Classification:
- Impact:
- Evidence:
- Attempts:
- Resolution or next action:
- Owner:
```
