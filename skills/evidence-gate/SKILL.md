---
name: evidence-gate
description: "Adversarially evaluate whether a strategy may advance, remain, or be demoted on the evidence ladder. Use after an experiment completes, before champion replacement, after suspicious results, or before any out-of-sample, walk-forward, or paper-stage promotion."
metadata:
  version: '0.1.0'
  core: 'true'
  mutable: 'false'
---

# Evidence Gate

Attempt to disprove the promotion case. The experiment runner does not review
its own promotion when an independent agent is available.

## Required Inputs

- preregistered experiment record
- immutable result artifacts
- data manifest version
- strategy specification and code commit
- prior related experiments
- requested evidence-stage transition

## Review Order

1. **Contract:** did execution match the preregistered design?
2. **Data:** did look-ahead, survivorship, revisions, or leakage contaminate results?
3. **Implementation:** do software tests and accounting invariants pass?
4. **Economics:** do returns survive costs, turnover, liquidity, and capacity assumptions?
5. **Statistics:** are sample size, uncertainty, dependence, purging, embargo,
   path dispersion, and multiple testing addressed?
6. **Robustness:** do nearby parameters, subperiods, regimes, and instruments support the mechanism?
7. **Independence:** was confirmation data untouched before the frozen evaluation?
8. **Risk:** are drawdown, concentration, exposure, and failure modes within policy?

## Output

```text
Decision: promote | keep | demote | discard | block
Requested transition:
Contract findings:
Validity findings:
Economic findings:
Statistical findings:
Risk findings:
Unresolved uncertainty:
Required next action:
```

## Invariants

- A failed validity check blocks promotion regardless of headline return.
- More trials raise, not lower, the evidence burden.
- Parameter cells and random seeds debit the trial budget.
- Purge and embargo periods must be positive when labels or features overlap time.
- Report a distribution over valid paths when the design creates multiple paths.
- Paper performance cannot retroactively validate a contaminated backtest.
- The reviewer may reject the promotion rule but cannot rewrite it after results.

## Completion Criterion

Every promotion criterion is traced to evidence, every validity failure is
resolved or blocking, and the decision is recorded without proof language.
