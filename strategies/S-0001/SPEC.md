# S-0001: Passive SPY Baseline

## Purpose

Provide the simplest investable baseline for validating evaluator timing,
transaction costs, accounting, and benchmark comparison.

## Rules

- Universe: SPY
- Signal: target 100% SPY after every session close
- Execution: next session open
- Direction: long only
- Rebalance: daily, although unchanged targets should create no additional trade
- Costs and risk: supplied by the preregistered manifest identifiers

This is infrastructure validation, not an alpha hypothesis.
