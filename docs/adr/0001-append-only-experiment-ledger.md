# ADR-0001: Append-Only Experiment Ledger

**Status:** Accepted
**Date:** 2026-08-05

## Context

Fresh agents need compact state, but compact state can erase discarded results,
failed attempts, and the path that produced the current champion.

## Decision

Use `EXPERIMENTS.jsonl` as the append-only historical source of truth and
`STATE.json` as a replaceable materialized operating view.

## Consequences

- Easier: reconstruct history and audit selection bias.
- Easier: give a fresh agent compact current context.
- Harder: state updates require referential-integrity validation.
- Impossible: silently erase a failed experiment without violating the contract.
