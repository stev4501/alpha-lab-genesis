# Market Data

The sealed daily-bar evaluator accepts CSV files with:

```text
date,symbol,open,high,low,close,volume
```

Rules:

- One row per symbol and session.
- Dates use `YYYY-MM-DD`.
- Prices are positive.
- Volume is non-negative.
- Every symbol must have the same session calendar for the initial evaluator.
- Adjustment and corporate-action semantics live in `DATA_MANIFEST.json`.
- The dataset path and SHA-256 checksum must match the manifest.

The strategy sees data through the current close and any resulting target weights
execute at the next session's open.
