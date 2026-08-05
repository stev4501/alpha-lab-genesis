# ADR-0004: Align Benchmark and Strategy Clocks

**Status:** Accepted
**Date:** 2026-08-05

## Context

`E-0001` exposed a comparison defect in `EV-0001`. The strategy first became
executable on the second session open because its first signal was produced
after the first session close. The benchmark instead began at the first session
open. Its extra session made net excess return unsuitable for decisions even
though execution timing and artifact integrity were otherwise valid.

Historical experiments must retain the system generation that produced them.
A generation transition must not rewrite or invalidate those records.

## Decision

Create `EV-0002` under `G-0002`. Measure benchmark return from the open of the
first session on which a strategy signal can be executed after a preregistered
warm-up through the final session close. Permit validated historical experiments
from prior generations to remain in the ledger while requiring pending
experiments to use the current generation.

Warm-up is owned by the versioned strategy as `WARMUP_SESSIONS`.
Preregistration pins that value, and execution rejects any mismatch.

## Consequences

- Easier: compare strategy and benchmark over the same executable interval.
- Easier: preserve `E-0001` as valid historical evidence of the defect.
- Harder: results from different generations require explicit interpretation.
- Impossible: use first-session benchmark exposure when the strategy could not
  yet hold a position.
