# Failures and Blockers

Retain failures because discarded evidence constrains future search.

## Open

### B-0003: Provider revision timing is unavailable

- First observed: `A-0006`
- Last observed: `2026-08-06`
- Classification: point-in-time provenance gap
- Impact: blocks D-0001 and D-0002 from historical session-close strategy evaluation
- Evidence: the finance connector exposes no publication timestamp, completed-bar flag, or revision identifier; repeated retrievals may revise values
- Attempts: D-0002 raw bytes, normalization, immutable snapshot, checksums, and dual-timestamp retrieval gating were preserved
- Resolution or next action: `A-0009` must obtain evidenced availability/revision semantics and machine-enforce them, or obtain human approval for a machine-enforced forward-only policy
- Owner: `data-integrity`

### B-0001: No validated point-in-time dataset

- First observed: genesis
- Impact: reopened by B-0003; blocks valid strategy experiments
- Evidence: D-0001 and D-0002 use a provider that exposes no publication, completion, or revision identifier
- Attempts: both datasets are preserved as immutable retrieval-time snapshots with point-in-time status unverified
- Resolution or next action: resolve with B-0003 through A-0009
- Owner: `data-integrity`

## Resolved

### B-0002: Benchmark clock differs from strategy clock

- First observed: `E-0001`
- Classification: evaluator contract mismatch
- Impact: blocks interpretation of net excess return
- Evidence: strategy enters on the second session open; benchmark begins on the first session open
- Attempts: `EV-0001` retained unchanged; no in-generation patch was made
- Resolution: `EV-0002` under `G-0002` aligns benchmark and strategy at the evaluation start
- Owner: `skill-lifecycle-governance`

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
