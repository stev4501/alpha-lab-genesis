# Tooling and Pattern Recommendations

The genesis repository intentionally starts with no heavy trading-engine
dependency. Data identity, evaluator sealing, and evidence policy must stabilize
before selecting infrastructure that would otherwise define those contracts by
accident.

## Patterns Incorporated into the Core

- **Autoresearch:** fixed-budget experiments, a sealed evaluator, explicit
  keep/discard/crash outcomes, and scope-limited modification
  ([repository](https://github.com/karpathy/autoresearch),
  [program](https://raw.githubusercontent.com/karpathy/autoresearch/master/program.md)).
- **Yoyo-evolve:** immutable core skills, commit-or-revert evolution,
  append-only archives plus derived active memory, and bounded scheduled sessions
  ([repository](https://github.com/yologdev/yoyo-evolve),
  [README](https://raw.githubusercontent.com/yologdev/yoyo-evolve/main/README.md)).
- **Qlib:** point-in-time revisions, configuration-defined runs, and standardized
  experiment records ([PIT documentation](https://qlib.readthedocs.io/en/latest/advanced/PIT.html),
  [workflow documentation](https://qlib.readthedocs.io/en/latest/component/workflow.html)).
- **Skfolio:** purged and embargoed validation paths plus explicit portfolio-risk
  measures ([CombinatorialPurgedCV](https://skfolio.org/generated/skfolio.model_selection.CombinatorialPurgedCV.html),
  [project](https://skfolio.org/)).
- **MLflow:** searchable run, parameter, metric, artifact, model, and dataset
  linkage ([tracking documentation](https://mlflow.org/docs/latest/ml/tracking/)).
- **NautilusTrader:** deterministic event-driven simulation and backtest/execution
  semantic parity ([backtesting concepts](https://nautilustrader.io/docs/latest/concepts/backtesting)).
- **Lean and Zipline Reloaded:** explicit fill, fee, slippage, margin, calendar,
  capital, bundle-vintage, and order-delay models
  ([Lean paper trading](https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/brokerages/quantconnect-paper-trading),
  [Zipline tutorial](https://zipline.ml4trading.io/beginner-tutorial.html)).

## Recommended Dependency Sequence

### First: no backtesting framework

Use the schemas, append-only ledger, and a trivial passive baseline to validate
data timestamps and accounting. This prevents framework defaults from becoming
unexamined research policy.

### Second: skfolio as a validation and risk dependency

Pin a reviewed release and wrap it behind the evidence gate. Override unsafe
zero purge and embargo defaults. Treat each parameter cell and random seed as a
trial, and retain the full path distribution rather than one equity curve
([Skfolio documentation](https://skfolio.org/generated/skfolio.model_selection.CombinatorialPurgedCV.html)).

### Third: Zipline Reloaded or a minimal daily-bar simulator

Use Zipline Reloaded when daily/minute event simulation, trading calendars,
slippage, transaction costs, and order delays are needed
([Zipline Reloaded](https://github.com/stefan-jansen/zipline-reloaded)). Keep it
behind the sealed evaluator so it can later be replaced.

### Fourth: MLflow as an index, not the source of truth

MLflow can make runs searchable, but the git-committed ledger and immutable
artifacts remain authoritative because the tracking documentation does not
establish append-only immutability ([MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/)).

### Later specialists

- **NautilusTrader:** use when event-level fidelity and backtest/paper parity
  justify its Rust/Python complexity ([repository](https://github.com/nautechsystems/nautilus_trader)).
- **QuantConnect Lean:** use when brokerage and order-model breadth justify the
  .NET and deployment surface ([repository](https://github.com/QuantConnect/Lean)).
- **Microsoft Qlib:** use as a point-in-time and workflow reference, or for
  factor/model research after its data model fits the chosen market
  ([repository](https://github.com/microsoft/qlib)).
- **Microsoft RD-Agent:** mine proposer/implementer separation and multi-seed
  reporting, but do not make its larger agent stack a Day 1 dependency
  ([repository](https://github.com/microsoft/RD-Agent)).

## Do Not Adopt

- **Quantopian Zipline:** obsolete upstream; prefer Zipline Reloaded
  ([repository](https://github.com/quantopian/zipline)).
- **Backtrader:** inactive and GPL-licensed for this use case
  ([repository](https://github.com/mementum/backtrader)).
- **mlfinlab:** retain its pipeline taxonomy, but not its restricted and stale
  public package ([repository](https://github.com/hudson-and-thames/mlfinlab)).
- **VectorBT as a default:** rapid parameter grids are useful but amplify
  multiple testing, and its Commons Clause requires a licensing review
  ([license](https://raw.githubusercontent.com/polakowo/vectorbt/master/LICENSE.md)).
- **FinRL on Day 1:** defer reinforcement learning until simpler hypotheses,
  accounting, and evidence controls are reliable
  ([repository](https://github.com/AI4Finance-Foundation/FinRL)).

## Recommended Core Roster

The repository now includes:

1. `genesis-orchestrator`
2. `hypothesis-engine`
3. `experiment-loop`
4. `data-integrity`
5. `evidence-gate`
6. `paper-execution`
7. `memory-handoff`
8. `skill-lifecycle-governance`
9. `anti-degradation-triage`

The first eight drive progress and preserve scientific validity.
`anti-degradation-triage` remains the immune system for skill failures.
