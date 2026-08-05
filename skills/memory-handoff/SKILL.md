---
name: memory-handoff
description: "Persist durable Alpha Lab state and prepare tomorrow's fresh agent. Use near session close, after experiments or blockers, after a crash recovery, or whenever STATE.json, the experiment ledger, decisions, failures, or artifact checksums must be synchronized."
metadata:
  version: '0.1.0'
  core: 'true'
  mutable: 'false'
---

# Memory and Handoff

Preserve decisions and evidence, not hidden reasoning or conversational residue.

## Storage Roles

- `EXPERIMENTS.jsonl`: append-only experiment truth.
- `STATE.json`: compact current operating view.
- `HYPOTHESES.md`: active, rejected, and parked hypotheses.
- `FAILURES.md`: recurring failures and unresolved blockers.
- `DECISIONS.md` and ADRs: append-only architectural choices.
- `results/` and `logs/`: immutable evidence artifacts.

## Close Procedure

1. Append final experiment records before updating materialized state.
2. Reconcile state references against ledger IDs and artifact paths.
3. Update blockers and action priorities.
4. Write one next action that fits a normal session and has a binary success criterion.
5. Record unresolved uncertainty and failed attempts.
6. Hash immutable artifacts.
7. Run `python scripts/validate_repository.py`.
8. Mark the run completed only after validation passes.

## Recovery Procedure

If state is missing or invalid:

1. Read the last valid experiment records.
2. Inspect immutable artifacts and the last run logs.
3. Rebuild the smallest valid `STATE.json`.
4. Set `dirty_shutdown` true until reconciliation passes.
5. Do not infer successful completion from an absent error.

## Invariants

- Summaries never replace source artifacts.
- Failed experiments and rejected hypotheses remain recoverable.
- No unsupported confidence is promoted into durable state.
- Tomorrow's agent receives one next action, not an unranked wish list.

## Completion Criterion

A fresh agent can identify current maturity, active blockers, last validated
evidence, and the next executable action without prior conversation context.
