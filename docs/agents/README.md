# Agent skill configuration

Per-repo configuration for the `mattpocock-skills` engineering skills, written
by `/mattpocock-skills:setup-matt-pocock-skills`.

| File | Read by |
| :--- | :--- |
| `issue-tracker.md` | `ask-matt`, `code-review`, `to-spec`, `to-tickets`, `triage`, `wayfinder` |
| `triage-labels.md` | `triage` |
| `domain.md` | any skill exploring the codebase — `ask-matt`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `improve-codebase-architecture`, `tdd`, `triage`, `wait-what` |

Consumer lists derived from the installed plugin at version 1.2.3 by grepping
its skills for references to these files and to `CONTEXT.md`. They may drift on
a plugin update; the files are read by name, so a stale list here costs nothing
functionally.

Edit these files directly to change the configuration. Re-running the setup
skill is only needed to switch issue trackers or start over.

## Who these apply to

**Humans working in this repository.** They do not apply to the autonomous
research sessions launched by `loop/run_session.sh`, which cannot use these
skills at all: the runner passes `--disable-slash-commands` and
`--disallowedTools "Skill"`, so no skill is reachable there. That agent's
workflow is defined by `loop/prompts/session.md` — select from `backlog/`,
escalate protected-path work through `core_change_requests/`, record in
`journals/`.

## The `## Agent skills` memory block was deliberately omitted

The setup skill's step 4 says that when neither `CLAUDE.md` nor `AGENTS.md`
exists, ask the user which to create — "don't pick for them". That question was
put to the operator along with the reasoning below, and the answer was
**neither**: write `docs/agents/` only. This is a recorded decision, not an
omission.

Both are auto-loaded project memory: Claude Code reads them at the start of
**every** session in this repository, the autonomous one included. A block
declaring "issues live in GitHub Issues, triage labels are `needs-triage`/…"
would become standing context for the research agent, contradicting the
workflow its own prompt gives it.

Nothing is lost by omitting it. The skills that need this configuration read
`docs/agents/*.md` directly; the memory block is a convenience pointer, not a
dependency.

If you later create `CLAUDE.md` or `AGENTS.md` for other reasons, keep this in
mind before adding the block — and note that anything in those files reaches the
loop agent, which is a governance decision under ADR-0009, not a formatting one.
