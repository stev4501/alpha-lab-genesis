---
name: paper-execution
description: "Operate and reconcile the paper portfolio under frozen execution and risk rules. Use when generating paper orders, simulating fills, marking positions, reconciling cash and holdings, enforcing risk limits, or recording forward performance."
metadata:
  version: '0.1.0'
  core: 'true'
  mutable: 'false'
---

# Paper Execution

Translate a frozen strategy into auditable simulated orders without live-market authority.

## Required Inputs

- promoted paper-stage strategy version
- paper account state
- approved market data
- execution clock
- cost model and risk policy
- current positions and open simulated orders

## Cycle

1. Verify account timestamp and market session.
2. Generate target positions from information available at signal time.
3. Apply exposure, concentration, liquidity, and drawdown limits.
4. Create deterministic simulated orders.
5. Simulate fills using the frozen fill and cost model.
6. Reconcile positions, cash, equity, realized and unrealized P&L.
7. Record rejected orders and risk-limit interventions.
8. Append immutable order, fill, and valuation artifacts.
9. Update `STATE.json` only after reconciliation balances.

## Accounting Invariants

- Ending cash equals beginning cash minus buys plus sells minus costs.
- Position quantity equals prior quantity plus signed fills.
- Equity equals cash plus marked position value.
- Gross exposure is non-negative and equals absolute position exposure.
- Drawdown is measured from prior peak equity.
- Every fill references exactly one simulated order.

## Safety Invariants

- No tool with live-order authority may be called.
- The skill never upgrades itself to live trading.
- Zero-cost or zero-slippage assumptions are invalid as promotion evidence.
- Missing prices, stale data, or reconciliation failure stop the cycle.
- Forward results remain separate from historical backtests.

## Completion Criterion

The paper account reconciles exactly, all risk checks are recorded, and the
forward-period artifacts can be independently replayed.
