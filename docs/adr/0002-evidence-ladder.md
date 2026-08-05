# ADR-0002: Evidence Ladder Instead of Proof Claims

**Status:** Accepted
**Date:** 2026-08-05

## Context

Finite historical and paper-trading results cannot guarantee future profitability.
A goal phrased as "prove a winner" rewards confirmation bias and metric gaming.

## Decision

Represent strategy maturity with reversible evidence stages and promotion gates.
Never store a boolean `proven` field.

## Consequences

- Easier: distinguish discovery results from forward evidence.
- Easier: demote strategies when later evidence fails.
- Harder: progress cannot be summarized as one success flag.
- Impossible: claim guaranteed future returns through the canonical schema.
