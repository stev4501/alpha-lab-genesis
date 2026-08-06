# Alpha Lab Scheduled-Task Specification

## Weekly strategy evolution

- Status: desired prompt update; not deployed by this transition
- Existing task ID: `d4809335`
- Cadence: Wednesday at 8:15 PM America/Chicago
- Budget: 90 minutes
- Maximum: one experiment or one complete capability increment
- Repository: `/home/user/workspace/alpha_lab_inspect/alpha-lab-genesis`
- Execution mode: foreground

### Task prompt

```text
Continue Alpha Lab Genesis from
`/home/user/workspace/alpha_lab_inspect/alpha-lab-genesis`, the writable source
of truth. The Mac copy and synchronization bundles are backups; do not depend on
local-device writes.

ORIENT
Read `MISSION.md`, `CONTEXT.md`, `STATE.json`, `DATA_MANIFEST.json`, the tail of
`EXPERIMENTS.jsonl`, `HYPOTHESES.md`, `DECISIONS.md`, `FAILURES.md`,
`CORE_MANIFEST.json`, and the skill named by the highest-priority executable
action in `STATE.json`.

RECOVER
Require a clean or deterministically recoverable Git state. Run the full test
suite and `scripts/validate_repository.py`. Stop and report if validation fails,
state cannot be recovered, or the next action requires human approval before it
may start. An action whose required output is an approval request may proceed.

SELECT
Use a 90-minute session budget and reserve at least ten minutes for closing.
Select the highest-priority action whose prerequisites are satisfied. Do not
trust next-action text embedded in this scheduled prompt; `STATE.json` is
authoritative. Only start an action whose estimate fits inside the session after
preserving the closing reserve. Complete at most one experiment or one bounded
capability increment. Prefer one complete evidence increment over multiple
partial changes.

EXECUTE
Remain paper-only. Never place or route live orders, access live-trading
credentials, rewrite experiment history, or claim future profitability is
proven. Require preregistration before evaluation, nonzero costs and slippage,
checksummed artifacts, explicit trial-budget accounting, and a separately
invoked adversarial reviewer before finalization. Record reviewer invocation
provenance. Cross-model review is skipped because this is a non-interactive
scheduled context. Under G-0003, do not generate, tune, or promote a strategy
through the proposed evolution path because reviewer independence and
statistical controls are not yet enforced by sealed components.

Only after an approved G-0004 implementation is installed:
- choose only from the machine-validated strategy grammar;
- change at most one conceptual strategy dimension per experiment;
- count every evaluated parameter configuration as a trial;
- do not use confirmation data for generation or tuning;
- reject duplicate or cosmetically modified hypotheses; and
- apply the preregistered multiple-testing rule.

PROTECT
Do not modify `MISSION.md`, protected schemas, core skills, sealed evaluator
components, or generation metadata without explicit human approval. If a sealed
change is necessary, write a narrow proposal and stop.

RECOVER FAILURES
Use one repository-scoped run occurrence ID. If execution cannot complete,
write an atomic failed-run checkpoint containing the occurrence ID, last valid
commit, diagnostics, recovery action, and dirty-shutdown state before releasing
the run. Never start a second scheduled writer without an approved lease or
compare-and-swap design.

CLOSE
Persist artifacts and handoff, update `STATE.json`, run tests and repository
validation again, commit the complete valid state transition, and leave the
repository clean. If validation fails, do not claim completion; preserve
diagnostics and report the blocker.

REPORT
Report only a verifiable artifact, blocker, validation failure, or approval
request. Include the experiment or change ID, outcome, important validity
findings, Git commit, exact next action, trials consumed, and confirmation
touches.
```

## Forward-evidence collector

- Status: inactive; do not schedule yet
- Proposed cadence: each US market day after the official close and after the
  selected data source is expected to be complete
- Activation gate: all six conditions in ADR-0007's forward-evidence collector
  activation predicate are machine-verified, then the user separately approves
  the recurring task
- Maximum: one immutable observation and one reconciliation transition

### Task contract

The collector may append market observations, calculate decisions from frozen
code, reconcile the simulated account, and evaluate preregistered kill criteria.
It cannot change evidence stage or strategy status; it emits a recommendation
for a separately authorized decision. It
must bind every observation, decision, simulated order, fill, valuation, and
reconciliation to a unique occurrence ID, immutable data vintage, frozen
strategy fingerprint, and frozen nonzero cost/slippage model. Retries must be
idempotent and exactly-once at the reconciliation boundary.

It must never generate or tune strategies, edit strategy code, consume
confirmation data for discovery, or change promotion criteria. Its checksummed
forward-evidence stream is distinct from discovery inputs. If a later hypothesis
uses an observed result, that lineage is tainted for the corresponding interval.

The exact scheduled time and task prompt must be finalized only after the data
all six ADR-0007 activation conditions are implemented and tested.
