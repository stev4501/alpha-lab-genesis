# ADR-0006: Content-Addressed Data Snapshots

**Status:** Accepted
**Date:** 2026-08-05

## Context

`DATA_MANIFEST.json` describes validated datasets but did not provide an
executable refresh path. Replacing a CSV in place would invalidate historical
experiments, while resolving only the latest file would create look-ahead risk.

## Decision

Register each retrieval under a new dataset ID in an append-only index. Copy its
bytes to a SHA-256-addressed path and resolve a named data series using the
latest snapshot whose market `as_of` is not later than the requested timestamp.

## Consequences

- Easier: reproduce the exact bytes available at a simulated decision time.
- Easier: detect mutation and prevent dataset-ID reuse.
- Harder: every refresh consumes storage and requires a new dataset ID.
- Impossible: silently replace a registered snapshot through the adapter.
