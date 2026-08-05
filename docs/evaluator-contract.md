# EV-0002 Daily-Bar Evaluator Contract

## Scope

EV-0002 is a sealed, long-only, daily-bar research evaluator. It is intentionally
smaller than a production trading engine.

## Clock

1. The strategy receives history through session \(t\)'s close.
2. It returns target weights after that close.
3. The evaluator executes the targets at session \(t+1\)'s open.
4. Positions are marked at session \(t+1\)'s close.
5. Strategy and benchmark returns begin at session \(t+1\)'s open.

This prevents same-close execution using information learned at that close.
Each strategy defines one positive integer `WARMUP_SESSIONS`. Preregistration
reads and pins that literal without executing strategy code. Before the pinned
count is satisfied, the evaluator builds history but does not request a signal.
Execution rejects any mismatch. The evaluation start is the next session open
after warm-up.

## Strategy Interface

```python
def target_weights(history, as_of):
    return {"SPY": 1.0}
```

`history` contains only rows available through `as_of`. Weights must be finite,
non-negative, within the preregistered position limit, and within gross exposure.

## Required Preregistration

- `evaluator_id: EV-0002`
- one validated dataset ID
- one validated universe ID
- one validated nonzero-slippage cost model
- one validated risk policy
- strategy entrypoint
- initial capital
- benchmark symbol
- positive integer `warmup_sessions`
- fixed time budget

## Immutable Outputs

- `metrics.json`
- `validity.json`
- `equity.csv`
- `trades.csv`
- `run.log`
- `artifact-manifest.json`
- optional `review.json`
- `finalization.json`

Existing outputs are never overwritten.
`run.log` records warm-up length, evaluation start, evaluation end, and benchmark
symbol so the common comparison interval is independently auditable.

## Promotion

Evaluation does not promote a strategy. A different agent records
`review.json`; promotion requires matching review and passed validity checks.
Finalization verifies checksums before appending the experiment ledger.

## Explicit Limitations

- Long-only integer shares
- One complete daily calendar shared by all symbols
- No shorting, leverage, borrow fees, taxes, dividends, or intraday fills
- No partial fills or volume participation model
- Benchmark return is first-executable-session open to final-session close

Experiments needing these features require a new evaluator generation rather
than silent extensions to EV-0002.
