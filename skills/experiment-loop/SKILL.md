---
name: experiment-loop
description: "Preregister and run one comparable strategy experiment under a fixed budget, then keep, discard, iterate, promote, demote, or block it. Use for every backtest, walk-forward evaluation, ablation, or controlled research change."
metadata:
  version: '0.1.0'
  core: 'true'
  mutable: 'false'
---

# Experiment Loop

Adapt the fixed-budget keep-or-discard discipline of autonomous research to
financial experiments without reducing validity to one metric.

## Required Inputs

- one falsifiable hypothesis
- validated dataset, universe, cost model, and risk policy identifiers
- frozen benchmark and evaluator definitions
- remaining session budget
- next available experiment ID

## Preregister

Before running:

1. Allocate an experiment ID.
2. Freeze code commit, environment, seed, data manifest version, and time budget.
3. Freeze system generation, evaluator ID, trial family, and parameter coordinates.
4. Debit every attempted parameter cell from the trial budget.
5. Freeze discovery and confirmation windows and any holdout access.
6. State signal and execution timestamps.
7. Freeze primary metric, secondary metrics, and promotion criteria.
8. Append a `preregistered` record or durable draft before observing results.

If any required input is missing, record a blocked experiment instead of improvising.

## Execute

1. Change one coherent factor per experiment.
2. Redirect verbose output to a log artifact.
3. Enforce the declared timeout.
4. Preserve crashes and invalid runs.
5. Never alter the evaluator or confirmation data to rescue a strategy.

## Decide

- `keep`: valid improvement at the current evidence stage.
- `discard`: valid experiment failed its rule.
- `iterate`: informative result justifies one named follow-up.
- `promote`: all promotion gates passed.
- `demote`: later evidence invalidated the current stage.
- `block`: infrastructure or validity prevented evaluation.

One favorable metric cannot override failed validity or risk gates.

## Persist

Append the final experiment record, write immutable result artifacts, update
state, and retain the prior strategy version.

## Invariants

- Comparable experiments use identical evaluation contracts.
- Confirmation data is not tuned against.
- Holdout access never exceeds the preregistered touch budget.
- Failed and crashed experiments remain visible.
- No unregistered experiment influences promotion.

## Completion Criterion

The ledger contains a complete record whose design predates its results, whose
decision follows the preregistered rule, and whose artifacts are reproducible.
