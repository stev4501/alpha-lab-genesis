---
name: skill-lifecycle-governance
description: "Govern creation, refinement, promotion, retirement, and versioning of Alpha Lab skills. Use when a repeated procedure suggests a new skill, a skill fails repeatedly, an optional specialist is proposed, or any core skill, schema, evaluator, or protected file might change."
metadata:
  version: '0.1.0'
  core: 'true'
  mutable: 'false'
---

# Skill Lifecycle Governance

Let the agent learn new procedures without silently changing the research system
that produced prior evidence.

## Required Inputs

- `CORE_MANIFEST.json`
- repeated-work or failure evidence from the ledger and logs
- candidate skill contract
- tests and affected callers
- current system generation

## Lifecycle

1. **Ad hoc:** perform a novel procedure directly and record what happened.
2. **Candidate:** after repeated need, draft scope, trigger, inputs, outputs,
   invariants, and completion criterion.
3. **Specialist:** validate and test the skill; keep it mutable and outside core.
4. **Core proposal:** require evidence that absence threatens validity or recovery.
5. **Retire:** preserve history and routing rationale; do not silently delete.

## Core Change Gate

Any change to a protected file, sealed component, or immutable core skill requires:

1. explicit human approval;
2. anti-degradation triage when prompted by failure;
3. behavioral and deterministic tests;
4. blast-radius review;
5. a new `system_generation`;
6. an ADR explaining comparability impact;
7. no direct comparison of results across generations without a bridge experiment.

## Invariants

- Core cannot modify its own mutability policy.
- A skill cannot grant itself live-order authority.
- A new skill must replace repeated work, not anticipated work.
- Instruction changes cannot alter historical experiment records.
- Sealed evaluator changes invalidate same-generation comparisons.

## Completion Criterion

The lifecycle action is versioned, tested, recorded, and either contained within
the current generation or accompanied by an approved generation transition.
