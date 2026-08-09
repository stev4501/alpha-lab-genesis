# Domain Docs

How the engineering skills should consume this repo's domain documentation when
exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the canonical vocabulary.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in.

This is a **single-context** repo: one `CONTEXT.md` and one `docs/adr/`, both at
the root. There is no `CONTEXT-MAP.md` and no per-package layout.

## File structure

```
/
├── CONTEXT.md
├── DECISIONS.md                       ← append-only index of the ADRs
├── docs/adr/
│   ├── 0001-append-only-experiment-ledger.md
│   ├── ...
│   └── 0009-agent-owned-operations.md
└── skills/  scripts/  evaluator/  strategies/
```

## Use the glossary's vocabulary

When your output names a domain concept — an issue title, a refactor proposal, a
hypothesis, a test name — use the term as defined in `CONTEXT.md`.

This repo is stricter than most about this, and `CONTEXT.md` says so explicitly.
It carries a **Banned Synonyms** section listing terms that must not be used:
`proven winner` (say "champion at <evidence stage>"), `test set` for market
confirmation data, `backtest result` without naming the evidence stage and data
snapshot, `profit` without stating gross/net/realized/simulated, `backtest
start` for return measurement (say "evaluation start"). Read that section before
writing anything that names a concept; drifting to a banned synonym is a
correctness error here, not a style preference.

If the concept you need isn't in the glossary, that's a signal — either you're
inventing language the project doesn't use (reconsider), or there's a real gap
(note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than
silently overriding:

> _Contradicts ADR-0007 (bounded strategy evolution loop) — but worth reopening
> because…_

## `CONTEXT.md` is human-owned; `docs/adr/` is not

The setup skill's default assumption is that `/domain-modeling` creates and
edits `CONTEXT.md` and ADRs lazily, as terms and decisions get resolved. That
holds for ADRs here. It does **not** hold for the glossary.

**`CONTEXT.md` is protected by two enforcing layers:**

| Surface | Effect |
| :--- | :--- |
| `.claude/settings.json` deny rules | `Edit`/`Write` on `CONTEXT.md` is refused at the point of the attempt |
| `loop/validate_session.sh` | a session branch touching it fails the gate |

`CODEOWNERS` also lists it, but that is not a third layer. ADR-0009 is explicit:
CODEOWNERS is "Convention, binding on nobody [...] permanently, since no
required-review setting will ever activate it." Human ownership is real, but it
rests on the two layers above plus the operator being the repository's only
admin — not on GitHub review mechanics.

So a skill that wants to change the glossary should **write the proposal to
`core_change_requests/` and stop there**, as `loop/prompts/session.md` instructs
the autonomous agent. The human applies it. An agent that tries to edit it
directly will be blocked, and one that works around the block is defeating a
deliberate control.

**`docs/adr/` carries none of those controls.** No deny rule, no entry in the
validator's protected-path regex, no `CODEOWNERS` line. A skill can write an ADR
directly. Under ADR-0009 the human owns "generation changes and freeze tags" and
the sealed core; individual ADRs are not in that enumerated set.

That said, an ADR is a governance artifact here, not a note. Prefer proposing
one through `core_change_requests/` when it changes how the loop or the evidence
ladder works, and reserve direct writes for decisions that only record what was
already agreed. This is a convention, not an enforced control — nothing will
stop you.

## If you do add an ADR

Two conventions the templates don't know about:

1. **Numbering is sequential.** `0001`–`0009` exist; the next is `0010`. Match
   the existing filename shape: `NNNN-kebab-case-title.md`.
2. **`DECISIONS.md` is the append-only index.** Add a line for the new ADR.
   `scripts/validate_repository.py` requires `DECISIONS.md` to *exist* — it does
   **not** check that every ADR is indexed there, so an unindexed ADR will not
   fail validation. Keeping the index complete is a convention the repository
   relies on for discoverability, not something enforced for you.
