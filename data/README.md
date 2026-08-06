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

## Immutable Snapshot Adapter

`scripts/register_market_snapshot.py` copies each retrieval to a
content-addressed path and appends one record to `data/snapshots/index.jsonl`.
The source file is never treated as the durable snapshot.

```bash
python scripts/register_market_snapshot.py register \
  --source data/SPY_2024-01-02_2025-12-31_1day.csv \
  --dataset-id D-0001 \
  --series-id SPY-1day \
  --as-of 2025-12-31T21:00:00Z \
  --retrieved-at 2026-08-05T15:24:03.592110Z

python scripts/register_market_snapshot.py resolve \
  --series-id SPY-1day \
  --as-of 2026-01-01T00:00:00Z

python scripts/register_market_snapshot.py validate
```

Every refresh must use a new `D-NNNN` identifier. Resolution returns the latest
valid snapshot whose `as_of` does not exceed the requested timestamp.
