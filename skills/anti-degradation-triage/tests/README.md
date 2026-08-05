# Six-Principle Workflow Tests

This suite has two layers:

1. `test_workflow.py` verifies the skill's structural invariants and the completeness
   of its behavioral fixtures.
2. `cases.json` defines black-box scenarios for evaluating an agent after it loads
   the skill.

## Run deterministic tests

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
agentskills validate .
```

Run both commands from the `anti-degradation-triage` directory.

## Run behavioral evaluations

For each case:

1. Start with a fresh agent context.
2. Load `anti-degradation-triage`.
3. Give the agent only the case's `scenario`.
4. Record the proposed classification, repair mode, actions, and completion evidence.
5. Compare the response with `expected`.

A case passes only when:

- the primary classification matches;
- the repair mode matches;
- every required action is present in substance;
- no forbidden action is proposed; and
- the response names evidence satisfying the completion criterion.

Do not require exact wording. These tests evaluate observable decisions, not prose.

## Coverage

The fixtures cover:

- insufficient and intermittent reproduction;
- Capability and Scope boundary precedence;
- Knowledge, Judgment, and Regression content defects;
- instance versus class-level repair;
- changing versus stable information;
- deletion, consolidation, and premature splitting;
- blast-radius checks and adjacent callers;
- unavailable change control; and
- checkpoint enforcement before save.
