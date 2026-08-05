# Required Capability Map

Persistent files store evidence. Skills supply judgment. Scripts enforce
mechanical contracts. All three are required for autonomous progress.

## Operating Capabilities

| Capability | Owner | Required inputs | Durable outputs | Must block when |
|---|---|---|---|---|
| Session control | `genesis-orchestrator` | mission, state, deadline, blockers | bounded run state, validated handoff | closing reserve cannot be protected |
| Hypothesis selection | `hypothesis-engine` | prior evidence, available data, active blockers | one falsifiable hypothesis | claim is duplicate, unfalsifiable, or future-aware |
| Experiment control | `experiment-loop` | hypothesis, frozen design, budget | preregistration, final ledger record, artifacts | design or evaluator is not frozen |
| Data governance | `data-integrity` | provider metadata and raw data | dataset, universe, cost, and risk records | timing, membership, revision, or provenance is unknown |
| Evidence review | `evidence-gate` | preregistration, results, lineage, prior trials | promote, keep, demote, discard, or block decision | validity or independence fails |
| Paper accounting | `paper-execution` | frozen strategy, prices, account, risk policy | orders, fills, positions, reconciled account | live-order authority, stale data, or imbalance appears |
| Memory and recovery | `memory-handoff` | ledger, artifacts, state, failures | compact state and next action | references or checksums do not reconcile |
| Self-modification safety | `anti-degradation-triage` | reproduced skill failure and expected behavior | classified repair or route-away | ownership, conflict, or validation is unresolved |
| Skill lifecycle | `skill-lifecycle-governance` | core manifest, repeated-work evidence, tests | create, refine, promote, retire, or generation transition | protected components would change without approval |

## Persistent-State Components

### MISSION.md

- **Role:** immutable constitution and safety boundary.
- **Required capability:** prevent objective drift and unauthorized live trading.
- **Writer:** human only.
- **Reader:** every agent at startup.
- **Failure mode:** if absent or modified without approval, stop.

### STATE.json

- **Role:** materialized current operating state.
- **Required capability:** expose maturity, active work, budgets, blockers, account
  state, and one next action in machine-readable form.
- **Writer:** orchestrator through atomic scripts.
- **Reader:** every skill.
- **Failure mode:** if invalid, recover from durable artifacts before research.

### EXPERIMENTS.jsonl

- **Role:** append-only final experiment ledger.
- **Required capability:** preserve selection history, including failures and crashes.
- **Writer:** experiment loop after finalization.
- **Reader:** hypothesis selection, evidence review, memory recovery.
- **Failure mode:** duplicate IDs, malformed records, or design/results ambiguity
  block promotion.

### HYPOTHESES.md

- **Role:** human-readable active, rejected, and parked hypothesis registry.
- **Required capability:** prevent duplicate search and preserve falsifiers.
- **Writer:** hypothesis engine and handoff.
- **Reader:** hypothesis and experiment skills.
- **Failure mode:** an idea not registered here cannot enter experimentation.

### DECISIONS.md and docs/adr/

- **Role:** append-only architecture and policy decisions.
- **Required capability:** preserve why evaluator, schema, and safety choices exist.
- **Writer:** agent with explicit authority or human.
- **Reader:** agents changing infrastructure or core skills.
- **Failure mode:** a cross-component policy change without an ADR cannot ship.

### FAILURES.md

- **Role:** unresolved blockers and recurring failure patterns.
- **Required capability:** prevent repeated dead ends and false clean slates.
- **Writer:** any owning skill through handoff.
- **Reader:** orchestrator at action selection.
- **Failure mode:** known critical blockers must outrank speculative research.

### DATA_MANIFEST.json

- **Role:** canonical identity and integrity status for datasets, universes, cost
  models, and risk policies.
- **Required capability:** point-in-time provenance and reproducible retrieval.
- **Writer:** data-integrity skill.
- **Reader:** every experiment and paper cycle.
- **Failure mode:** an unvalidated dependency blocks affected experiments.

### CORE_MANIFEST.json

- **Role:** immutable core roster and research-system generation boundary.
- **Required capability:** prevent silent evaluator or core-contract drift.
- **Writer:** approved generation-transition workflow.
- **Reader:** startup, experiment, evidence, and skill-lifecycle gates.
- **Failure mode:** undeclared core changes invalidate same-generation comparison.

### strategies/

- **Role:** versioned strategy specifications, code, and tests.
- **Required capability:** separate strategy identity from experiment instances.
- **Writer:** experiment implementation workflow.
- **Reader:** experiment, evidence, and paper skills.
- **Failure mode:** unversioned strategy changes invalidate comparisons.

### results/

- **Role:** immutable artifacts for each experiment.
- **Required capability:** independent replay and audit.
- **Writer:** experiment and paper workflows.
- **Reader:** evidence gate and recovery.
- **Failure mode:** missing checksums or overwritten artifacts block promotion.

### logs/

- **Role:** detailed run, tool, crash, and execution traces.
- **Required capability:** diagnose failures without bloating active state.
- **Writer:** tools and orchestrator.
- **Reader:** recovery and anti-degradation triage.
- **Failure mode:** a failed run without diagnostic evidence becomes an explicit blocker.

### skills/

- **Role:** routable judgment and workflow modules.
- **Required capability:** keep responsibilities narrow and independently testable.
- **Writer:** approved skill-change workflow.
- **Reader:** orchestrator and specialized agents.
- **Failure mode:** immutable core skill modification without approval stops the run.

### schemas/, scripts/, and tests/

- **Role:** deterministic enforcement.
- **Required capability:** validate state shape, references, deadlines, identifiers,
  and package integrity.
- **Writer:** engineering workflow with tests.
- **Reader:** startup and handoff gates.
- **Failure mode:** any failing deterministic check blocks completion.

## Day 1 Dependency Order

1. Validate repository integrity.
2. Validate one point-in-time dataset.
3. Register an effective-dated investable universe.
4. Freeze cost and risk policies.
5. Establish passive and strategy-specific baselines.
6. Run the first discovery experiment.
7. Apply the evidence gate.
8. Begin paper execution only after earlier gates pass.

Parallelism must not bypass this dependency order.
