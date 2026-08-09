# Agent skill configuration

Per-repo configuration for the `mattpocock-skills` engineering skills, written
by `/mattpocock-skills:setup-matt-pocock-skills`.

| File | Read by |
| :--- | :--- |
| `issue-tracker.md` | `ask-matt`, `code-review`, `to-spec`, `to-tickets`, `triage`, `wayfinder` |
| `triage-labels.md` | `triage` |
| `domain.md` | any skill exploring the codebase — `ask-matt`, `diagnosing-bugs`, `domain-modeling`, `improve-codebase-architecture`, `tdd`, `to-spec`, `to-tickets`, `triage`, `wait-what` |

Consumer lists derived from the installed plugin at version 1.2.3 by reading
each `SKILL.md` for an instruction to use the glossary, ADRs, the issue tracker,
or the label vocabulary — not by grepping filenames, which misses `to-spec` and
`to-tickets` (they say "the project's domain glossary" without naming
`CONTEXT.md`) and wrongly catches `codebase-design` (the match is in a reference
file, not an instruction). The lists may drift on a plugin update; nothing
depends on them being current.

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

### What replaces it

Something had to. Most of these skills say "the issue tracker should have been
provided to you — run `/setup-matt-pocock-skills` if not" and never name a path;
only `code-review` references `docs/agents/issue-tracker.md` directly. The
memory block is how the setup skill normally provides it, so dropping it without
a replacement would leave `to-spec`, `to-tickets`, `triage`, and `wayfinder`
unable to find this configuration — they would ask for setup to be re-run, which
would rewrite these files and change nothing.

`bin/dev-session` supplies the pointer instead, passing
`--append-system-prompt-file docs/agents/session-prompt.md`. That text lives in
a file precisely so the direct route can carry the same pointer with one extra
flag rather than reproducing a paragraph by hand.

**The claim is about wrapper-launched sessions, not all sessions that can load
the plugin.** The wrapper itself points at a direct invocation for anyone who
wants headless-with-skills, and that route loads the plugin. It carries the
configuration only if it also passes the flag:

```bash
claude --plugin-dir dev/plugins/mattpocock-skills \
       --append-system-prompt-file docs/agents/session-prompt.md
```

Omitting the second flag is a supported opt-out with a known consequence: the
skills load and their configuration does not, so `to-spec`, `to-tickets`,
`triage`, and `wayfinder` will ask for `/setup-matt-pocock-skills` to be re-run.
The wrapper's refusal message prints the full two-flag command for this reason.

What *is* true unconditionally is the direction that matters for safety: the
autonomous runner invokes neither the wrapper nor `--plugin-dir`, and strips
skills regardless. `tests/test_dev_plugins.py` asserts the wrapper keeps passing
the pointer, checking the emitted argv rather than the script text.

If you later create `CLAUDE.md` or `AGENTS.md` for other reasons, keep this in
mind before adding the block — and note that anything in those files reaches the
loop agent, which is a governance decision under ADR-0009, not a formatting one.
