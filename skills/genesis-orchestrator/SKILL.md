---
name: genesis-orchestrator
description: "Run a bounded autonomous Alpha Lab session from orientation through validated handoff. Use whenever a fresh agent awakens, resumes the mission, chooses the next action, coordinates core skills, or approaches its session deadline."
metadata:
  version: '0.1.0'
  core: 'true'
  mutable: 'false'
---

# Genesis Orchestrator

Own the session, not the finance method. Delegate domain work to the relevant
core skill and ensure each run leaves a validated artifact.

## Required Inputs

- `MISSION.md`
- `CONTEXT.md`
- `STATE.json`
- `DATA_MANIFEST.json`
- tail of `EXPERIMENTS.jsonl`
- `HYPOTHESES.md`, `DECISIONS.md`, and `FAILURES.md`
- remaining wall-clock budget

## Session Loop

### Orient

1. Run `python scripts/validate_repository.py`.
2. If `run.dirty_shutdown` is true, recover state before new research.
3. Read open critical blockers and the last handoff.
4. Confirm all required tools are approved and paper-only.

### Select

Choose the executable action with:

1. satisfied prerequisites;
2. highest blocker severity;
3. highest expected information gain;
4. enough time to execute and close safely.

Do not optimize for visible activity or number of experiments.

### Execute

Dispatch exactly one primary objective at a time. Parallel work is allowed only
when artifacts cannot conflict and the closing reserve remains protected.

### Reassess

After each artifact, update state and decide whether enough budget remains for
another bounded action. Never begin an action whose estimate would consume the
closing reserve.

### Close

1. Stop new work when the reserve begins.
2. Persist artifacts and checksums.
3. Append completed experiment records.
4. Update `STATE.json`, `HYPOTHESES.md`, `FAILURES.md`, and decisions as needed.
5. Name one next executable action with a success criterion.
6. Run repository validation.
7. Mark the run completed only after validation passes.

## Invariants

- No live orders.
- No silent deletion or rewriting of experiment history.
- No experiment begins without preregistration.
- No session ends without a deterministic handoff or an explicit dirty shutdown.
- `MISSION.md` and immutable core skills are not autonomously modified.

## Completion Criterion

The run leaves a verifiable artifact, a valid materialized state, and one
unambiguous next action that a fresh agent can execute without conversation history.
