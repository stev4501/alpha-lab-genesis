# ADR-0005: Finalization Closes the Session

**Status:** Accepted
**Date:** 2026-08-05

## Context

`E-0002` completed and entered the ledger, but finalization left the run marked
dirty and retained the prior next action. That made a successful session appear
interrupted and prevented the next agent from resuming deterministically.

## Decision

Under `G-0003`, successful idempotent finalization closes the run, clears the
dirty marker, records the finalized baseline, and replaces the action queue with
the decision's exact next action. Replaying finalization repairs closeout state
without incrementing experiment counters.

## Consequences

- Easier: scheduled agents can distinguish completion from interruption.
- Easier: the handoff and action queue agree with the experiment decision.
- Harder: finalization owns more of the session-state transition.
- Impossible: leave a successfully finalized run dirty without validation
  detecting stale state.
