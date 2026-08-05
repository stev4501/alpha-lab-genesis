---
name: anti-degradation-triage
description: >-
  Triage QA feedback before patching any skill. Use when a skill produces bad
  output, QA finds a failure, a user complains, a prior edit regresses behavior,
  or you are tempted to add another rule. Prevents bloat and regression through
  reproduction, ownership checks, defect classification, root-cause repair, and
  contract verification. After triage confirms a skill edit is needed, prefer
  `skill-change-control`; if unavailable, use the validated `create-skill`
  save workflow and disclose the missing change-control owner.
metadata:
  author: stevan-davila
  version: '3.1'
---

# Anti-Degradation Triage

Do not patch the latest symptom. Reproduce the failure, establish ownership,
classify its mechanism, repair the narrowest root cause, reduce unnecessary
complexity, and verify surrounding contracts.

## When to Use

Use this before modifying a skill in response to QA feedback, test failures,
user complaints, regressions, observed bad output, or the urge to add an
`always` or `never` rule.

Do not use it for a planned new capability with no observed failure. Route
ordinary skill changes to the standard skill creation or change-control workflow.

## The Six Principles

Follow these in order. Each principle produces the evidence required by the
next one.

### Reproduce Before Repairing

Capture:

- the exact input;
- the actual output or behavior;
- the expected output or behavior;
- whether the failure is consistent;
- the smallest case that still fails.

Do not edit from a vague complaint. If the failure cannot be reproduced, gather
more evidence or classify it as intermittent; do not invent a permanent rule.

**Completion criterion:** another agent could rerun the case and distinguish
pass from fail.

### Establish Capability and Ownership

Check the boundary before inspecting instruction content:

1. **Could any wording in this skill have prevented the failure?**
   - No: **Capability Gap.** The environment, permission, model, tool, rate
     limit, or data source failed. Route it to that owner. Do not edit the skill,
     except for one narrow graceful-degradation instruction when silent failure
     is itself the defect.
   - Yes: continue.
2. **Is the failing case part of this skill's stated job?**
   - No: **Scope Gap.** Narrow the trigger, decline the case, or route to the
     correct owner. Do not teach this skill the other owner's job.
   - Yes: continue.

Boundary failures should shrink or bypass the skill, not grow it.

**Completion criterion:** the responsible component is named, and this skill
either owns the repair or has a concrete route-away action.

### Classify the Defect Mechanism

For failures the skill owns, choose one primary mechanism:

| Type | Diagnostic question | Repair direction |
|---|---|---|
| **Knowledge Gap** | Was a required fact, convention, format, or constraint absent? | Add the narrow missing information with the reason it matters. |
| **Judgment Gap** | Were the facts available, but timing, depth, priority, or fit misjudged? | Rewrite the existing instruction as a calibrated tradeoff. |
| **Behavioral Regression** | Did a prior edit or competing instruction break behavior that previously worked? | Remove or merge the conflict; do not add an arbitration rule. |

If the content types remain ambiguous, prefer **Judgment Gap** only after
Capability and Scope have been ruled out. Calibrating an owned decision is safer
than expanding scope.

**Completion criterion:** one primary issue type is selected and supported by
evidence from the reproduced case.

### Fix the Narrowest Root Cause

Choose between an instance repair and a class-level repair:

| Type | Instance repair | Class-level repair |
|---|---|---|
| **Knowledge Gap** | Add a stable missing fact with a because-clause. | Resolve fast-changing facts at run time from one maintained source. |
| **Judgment Gap** | Replace vague or binary wording with when/why calibration. | Remove or externalize the ambiguous choice so it cannot recur. |
| **Behavioral Regression** | Merge competing constraints into one ordered principle. | Assign constraints to distinct ordered steps so they cannot collide. |

Use a class-level repair when the failure recurs or the skill embeds information
that changes faster than the skill. Use an instance repair when the fact is
stable and recurrence is unlikely. Do not build machinery for a hypothetical
future failure.

Every repair must explain why it produces the expected behavior. A naked rule
solves only the remembered example.

**Completion criterion:** the proposed change addresses the diagnosed mechanism,
and its scope is no broader than the evidence justifies.

### Prefer Deletion and Consolidation

Before adding instructions, try these moves in order:

1. Rewrite an existing instruction.
2. Merge overlapping instructions into one authoritative statement.
3. Delete no-ops, obsolete exceptions, and historical scaffolding.
4. Move rare or bulky branch detail behind a reference that states when to read it.
5. Add a new instruction only when no existing instruction can carry the behavior.

Keep each normative concept in one authoritative location. Repeat it only when
the occurrences have distinct execution roles, such as invocation, procedure,
and completion gate, and the repetition prevents a named failure.

Pair prohibitions with the required action when prohibition alone leaves the
next step unclear.

Do not split a skill merely because it is long. First prune, improve information
hierarchy, and sharpen completion criteria. Split only when the extracted
responsibility needs independent invocation or a real handoff boundary, and the
benefit exceeds the added routing and cognitive cost. Renames, merges, and splits
require explicit user approval.

**Completion criterion:** instruction count stays flat or decreases unless one
new instruction is demonstrably required, and each remaining instruction changes
a decision or observable behavior.

### Verify Behavior and Surrounding Contracts

After editing:

1. Rerun the reproduced case.
2. Test adjacent cases that depend on the old behavior.
3. Scan the full skill for duplication and contradiction.
4. Search complementary skills and callers for the exact skill name and close
   aliases.
5. Change complementary skills only when their existing contract is broken.
6. Run `agentskills validate` on the skill directory.
7. Hand an owned edit to `skill-change-control`. If that skill is unavailable,
   disclose the capability gap and use the validated `create-skill` save workflow
   only when the user explicitly requested the edit.

For every non-trivial edit, record:

```markdown
Anti-degradation checkpoint:
- Issue type: Capability | Scope | Knowledge | Judgment | Regression
- Boundary result: why this skill owns the change, or where it was routed
- Root-cause choice: instance repair or class-level repair, with rationale
- Blast radius: complementary skills/callers checked and outcome
- Preserved invariants: old behaviors that must remain true
- Bloat result: instruction count change and justification
- Behavioral validation: reproduced and adjacent cases
- Package validation: agentskills validate result
```

Do not save when a checkpoint field is missing, an old invariant remains
unresolved, an affected caller has not been checked, or validation fails.

**Completion criterion:** the target case passes, surrounding contracts remain
intact, and the checkpoint is complete.

## Compact Examples

- **Capability:** Calendar retrieval fails because its connector is disconnected.
  Report the dependency failure; do not add calendar-retrieval prose.
- **Scope:** A commit-message skill is asked to review a pull request. Narrow its
  trigger or route to the review skill; do not add review behavior.
- **Knowledge:** An ingestion pipeline requires a date-prefixed filename. Add the
  exact format and explain that parsing depends on the prefix.
- **Judgment:** A quick status request produces a two-page report. Replace “be
  thorough” with depth calibrated to decision and audit weight.
- **Regression:** A new brevity limit suppresses mandatory alarm context. Merge
  both constraints into one principle that preserves required context before
  optimizing length.

## Final Gate

The triage is complete only when:

- the failure is reproducible;
- capability and ownership are resolved;
- one primary mechanism is identified;
- the repair is proportional to evidence;
- duplication and unnecessary complexity did not increase;
- target behavior and surrounding contracts pass validation; and
- the owned edit is handed to change control, or its disclosed fallback is used.
