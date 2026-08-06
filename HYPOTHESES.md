# Hypotheses

## Active

### H-0001: Infrastructure before alpha

If the agent first establishes a point-in-time universe, an explicit execution
clock, realistic costs, and a passive baseline, then later strategy comparisons
will be reproducible and less vulnerable to false improvement.

- Status: active
- Evidence stage: bootstrap
- Falsifier: the infrastructure cannot reproduce identical baseline results from
  the same manifest, code version, and seed.
- Next experiment: blocked until the first dataset is validated.

#### E-0001 observation

The real-data baseline completed, but its excess-return comparison is invalid:
the strategy entered at the second session's open while the benchmark began at
the first session's open. The evaluator correctly enforced next-open execution,
but the benchmark clock must be aligned before this hypothesis can advance.

- Experiment: `E-0001`
- Decision: block
- Preserved result: all execution and checksum artifacts remain immutable
- Next action: request approval for `EV-0002` under `G-0002`

#### G-0002 transition

Human approval authorized `EV-0002` under `G-0002`. The evaluator now defines
the evaluation start as the first session on which the initial signal can be
executed after strategy-owned warm-up and begins the benchmark at that same
open. `S-0002` is the versioned passive baseline with an explicit warm-up
contract. `E-0001` remains immutable.

#### A-0005 capability increment

The data refresh boundary now registers each retrieval under a new dataset ID,
copies bytes to a SHA-256-addressed path, and resolves the latest snapshot whose
market `as_of` does not exceed the requested timestamp. `D-0001` is registered
as the first immutable snapshot, and `DATA_MANIFEST.json` uses that snapshot as
its canonical path.

- Artifact: `data/snapshots/index.jsonl`
- Validation: 20 tests, registry validation, repository validation, and independent review passed
- Next action: retrieve and register current SPY daily data as `D-0002`

## Rejected

None.

## Parking Lot

- Cross-sectional quality and momentum composite
- Medium-term trend following with volatility scaling
- Post-earnings drift using publication-aware timestamps

Parking-lot entries are not approved experiments. They must be converted into
falsifiable hypotheses and preregistered before execution.
