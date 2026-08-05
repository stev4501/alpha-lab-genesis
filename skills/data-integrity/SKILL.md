---
name: data-integrity
description: "Register and validate market datasets, investable universes, costs, and timestamps before strategy research. Use when adding or refreshing data, changing providers, defining a universe, investigating suspicious performance, or resolving any data-integrity blocker."
metadata:
  version: '0.1.0'
  core: 'true'
  mutable: 'false'
---

# Data Integrity

No strategy result outranks the integrity of the data that produced it.

## Required Inputs

- approved retrieval tool and provider
- requested fields, frequency, date range, and universe
- provider documentation or metadata
- current `DATA_MANIFEST.json`

## Dataset Checks

1. Record retrieval time, market as-of time, timezone, fields, and checksum.
2. Determine whether each field is point-in-time or revised.
3. Verify symbol changes, delistings, splits, dividends, and corporate actions.
4. Verify universe membership is effective-dated rather than current-membership only.
5. Measure missingness, duplicates, timestamp ordering, and impossible values.
6. State adjustment and revision policies.
7. Record license and permitted use.
8. Mark status `validated` only when every critical check has evidence.

## Trading-Clock Contract

Every signal must name:

- when input became public;
- market timezone;
- earliest permissible order time;
- fill assumption;
- holiday and session calendar.

## Tool Rule

Use approved structured finance-data tools for prices and financial data. Web
pages may support qualitative research but are not canonical market datasets.

## Invariants

- Current index membership cannot stand in for historical membership.
- Restated fundamentals cannot be treated as originally reported values.
- Adjusted prices and raw corporate actions cannot be mixed without an explicit rule.
- A missing integrity claim is `unverified`, never implicitly true.

## Completion Criterion

The manifest contains enough provenance and validation evidence for an independent
agent to retrieve or identify the same dataset and reproduce its timing semantics.
