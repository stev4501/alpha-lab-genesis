Developer skill configuration for this repository lives in `docs/agents/`:

- `docs/agents/issue-tracker.md` — GitHub issues are the human queue; `backlog/`
  is the autonomous loop's separate queue. Includes the read/write commands and
  the wayfinding layout.
- `docs/agents/triage-labels.md` — the triage label vocabulary.
- `docs/agents/domain.md` — glossary and ADR rules, including which files are
  human-owned and must be proposed through `core_change_requests/`.

Skills that expect an issue tracker, a triage label vocabulary, or a domain-doc
layout to have been provided should read those files rather than asking for
`/setup-matt-pocock-skills` to be re-run.
