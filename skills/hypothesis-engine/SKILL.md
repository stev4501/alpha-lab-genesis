---
name: hypothesis-engine
description: "Generate, falsify, and prioritize stock-strategy hypotheses. Use when the action queue lacks a sufficiently specific experiment, a research path stalls, or failed results require a new explanation rather than another parameter tweak."
metadata:
  version: '0.1.0'
  core: 'true'
  mutable: 'false'
---

# Hypothesis Engine

Convert market observations into falsifiable claims. Do not produce ticker tips.

## Required Inputs

- evidence stage and blockers from `STATE.json`
- validated datasets and universes from `DATA_MANIFEST.json`
- active, rejected, and parking-lot entries in `HYPOTHESES.md`
- prior experiment outcomes

## Process

1. Identify a proposed mechanism, not merely a correlation.
2. State what information would have been available at signal time.
3. Define the expected direction, horizon, universe, and failure condition.
4. Name the simplest null or baseline explanation.
5. Search prior experiments for duplicates and near-duplicates.
6. Score candidates from 0 to 1 on:
   - falsifiability;
   - expected information gain;
   - data readiness;
   - implementation cost;
   - independence from previously tested ideas.
7. Promote one candidate into an experiment draft.

## Output

```text
Hypothesis ID:
Claim:
Mechanism:
Available-at timestamp:
Expected effect:
Universe:
Horizon:
Null baseline:
Falsifier:
Required data:
Expected information gain:
```

## Invariants

- A hypothesis cannot contain future-aware inputs.
- Rephrasing a failed hypothesis does not make it new.
- Parameter sweeps count as multiple tests.
- Popularity, narrative appeal, and recent returns are not evidence.

## Completion Criterion

One non-duplicate hypothesis is specific enough for `experiment-loop` to
preregister without inventing missing design choices.
