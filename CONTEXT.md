# CONTEXT

Use these terms exactly in skills, state, code, logs, and handoffs.

## Terms

### Hypothesis
A falsifiable claim connecting a market feature to an expected, measurable
outcome. Not a strategy idea, intuition, or ticker preference.

### Experiment
One preregistered execution of a hypothesis under a fixed design, data snapshot,
code version, budget, and decision rule.

### Baseline
The simplest valid strategy or benchmark against which an experiment is judged.
SPY may be a market benchmark, but a strategy-specific null baseline is also
required when appropriate.

### Champion
The currently best strategy at a specific evidence stage. Champion does not mean
proven or approved for live trading.

### Discovery data
Data permitted for hypothesis generation and tuning.

### Confirmation data
Untouched data reserved for evaluating a frozen strategy. Do not call it test
data when that could be confused with software tests.

### Point-in-time data
Data represented as it was knowable at the simulated decision timestamp,
including publication lag, revisions, delistings, and corporate actions.

### Evidence stage
One state in the evidence ladder: `bootstrap`, `baseline`, `discovery`,
`out_of_sample`, `walk_forward`, or `paper`.

### Promotion gate
A preregistered set of criteria required to advance a strategy to the next
evidence stage.

### Materialized state
`STATE.json`, the compact current operating view. It is derived and replaceable,
not the historical source of truth.

### Experiment ledger
`EXPERIMENTS.jsonl`, the append-only source of truth for experiment history.

### Handoff
The validated state left for the next fresh agent: what changed, what remains
uncertain, and the single next executable action.

## Banned Synonyms

- Do not use `proven winner`; use `champion at <evidence stage>`.
- Do not use `test set` for market confirmation data.
- Do not use `backtest result` without naming the evidence stage and data snapshot.
- Do not use `profit` without stating whether it is gross, net, realized, or simulated.
