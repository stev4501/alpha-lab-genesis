# Failures and Blockers

Retain failures because discarded evidence constrains future search.

## Open

### B-0002: Benchmark clock differs from strategy clock

- First observed: `E-0001`
- Classification: evaluator contract mismatch
- Impact: blocks interpretation of net excess return
- Evidence: strategy enters on the second session open; benchmark begins on the first session open
- Attempts: none; the sealed evaluator was not modified after results
- Resolution or next action: request approval for `EV-0002` and `G-0002`
- Owner: `skill-lifecycle-governance`

### B-0001: No validated point-in-time dataset

- First observed: genesis
- Impact: resolved; previously blocked valid strategy experiments
- Evidence: `DATA_MANIFEST.json` contains no validated dataset
- Resolution: `D-0001` registered and validated for price-return evaluation
- Owner: `data-integrity`

## Resolved

None.

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
