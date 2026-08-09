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

## Both targets are human-owned: propose, don't apply

The setup skill's default assumption is that `/domain-modeling` creates and
edits `CONTEXT.md` and ADRs lazily, as terms and decisions get resolved. **That
does not hold here.**

Under ADR-0009 the human owns the core. `CONTEXT.md` and `docs/adr/` are
protected in three places at once:

| Surface | Effect |
| :--- | :--- |
| `.claude/settings.json` deny rules | `Edit`/`Write` on `CONTEXT.md` is refused at the point of the attempt |
| `loop/validate_session.sh` | a session branch touching them fails the gate |
| `CODEOWNERS` | changes require review by the operator |

So a skill that wants to change the glossary or add an ADR should **write the
proposal to `core_change_requests/` and stop there**, exactly as
`loop/prompts/session.md` instructs the autonomous agent. The human applies it.
An agent that tries to edit these files directly will be blocked, and one that
works around the block is defeating a deliberate control.

## If you do add an ADR

Two conventions the templates don't know about:

1. **Numbering is sequential.** `0001`–`0009` exist; the next is `0010`. Match
   the existing filename shape: `NNNN-kebab-case-title.md`.
2. **`DECISIONS.md` is the append-only index** and is required by
   `scripts/validate_repository.py`. An ADR added without a corresponding
   `DECISIONS.md` entry leaves the repository inconsistent, which the next
   selfcheck may surface — and a failed selfcheck puts the autonomous loop into
   maintenance mode rather than research mode.

Both files are human-owned, so in practice this means the *proposal* you write
to `core_change_requests/` should include the ADR body and the `DECISIONS.md`
line to append, ready for the human to apply together.
