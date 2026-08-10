# Developer-only skills

How third-party Claude Code skills are made available to humans working in this
repository without becoming usable by the autonomous research sessions launched
by `loop/run_session.sh`.

The dedicated **Alpha Lab Dev** cloud environment installs these skills for
supervised sessions. The autonomous loop does not use that environment and
removes the `Skill` tool independently.

## The requirement

Third-party skill collections are useful during supervised development. They are
actively harmful on the autonomous path. Several skills in the currently
vendored collection (`implement`, `prototype`, `research`, `to-tickets`,
`wizard`) instruct an agent to scope new work and build it self-directedly,
which is the precise opposite of the mandate in `loop/prompts/session.md`:

> Do NOT start new strategy experiments, register hypotheses, or touch holdout
> data — the current phase is loop-proving maintenance only.
> [...] One unit of work per session.

So the requirement is not "prefer that the loop agent ignore these." It is that
the loop agent must not see them at all — not their bodies, and not their
descriptions.

## Where Claude Code finds skills

Claude Code discovers skills from exactly these locations:

| Level | Path | Loaded when |
| :--- | :--- | :--- |
| Personal | `~/.claude/skills/<name>/SKILL.md` | Always, all projects |
| Project | `.claude/skills/<name>/SKILL.md` | Always, this project |
| Nested project | `<subdir>/.claude/skills/<name>/SKILL.md` | When Claude reads or edits a file under `<subdir>` |
| Additional dir | `<added-dir>/.claude/skills/<name>/SKILL.md` | When passed via `--add-dir` |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Where the plugin is enabled |

Two consequences matter here.

First, this repository's nine core skills live at **`skills/<name>/SKILL.md`** —
repo root, not under `.claude/`. That is not a discovery path. The core skills
are never registered as Claude Code skills at all; sessions read them with the
`Read` tool, as `loop/prompts/session.md` directs. **This repository therefore
makes no use of the `Skill` tool.**

Second, `.claude/skills/` would be the wrong home for vendored skills, because
project skills load into *every* session in the repository, `claude -p`
included.

## The arrangement

The plugin is vendored at `dev/plugins/mattpocock-skills/`, which is not a
discovery path at any level. The vendored tree is the reviewed source and
provenance reference. `dev/cloud/setup-mattpocock-skills.sh` creates a private
marketplace pinned to the same upstream commit, installs it in the dedicated
cloud environment, and verifies the installed SHA and enabled state.

The setup also writes user-level memory beneath `CLAUDE_CONFIG_DIR`. That memory
tells supervised Alpha Lab sessions to read `docs/agents/session-prompt.md`,
which points the engineering skills at the repository issue tracker, triage
vocabulary, and domain docs. See `docs/agents/README.md`.

### Cloud and web sessions: environment-scoped delivery

Repository plugin declarations were tried and disproved, but the dedicated
**Alpha Lab Dev** cloud environment installs the pinned plugin and configuration
pointer explicitly before Claude launches. First-session direct and subagent
invocation, configuration loading, and second-session cached reuse are governed
by `.claude/cloud-environment-plugin-acceptance.json`.

#### `enabledPlugins` does not work — tested, twice

The Claude Code docs list three ways a cloud session can receive skills: the
repo's `.claude/skills/`, a plugin declared in the repo's
`.claude/settings.json`, or skills enabled for your claude.ai account. The
second looked ideal, so it was tried:

```json
"enabledPlugins": { "mattpocock-skills@claude-plugins-official": true }
```

A fresh cloud session started on the branch carrying that declaration reported:

| Probe | Result |
| :--- | :--- |
| skills matching "mattpocock" | **NO** — zero matches in the registry |
| `cat ~/.claude/plugins/installed_plugins.json` | `No such file or directory` |
| `ls ~/.claude/plugins/marketplaces` | `No such file or directory` |
| invoking `/mattpocock-skills:tdd` | `Unknown skill: mattpocock-skills:tdd` |

Reproduced locally from clean plugin state (fresh clone,
`CLAUDE_CONFIG_DIR` with no `plugins/`): `claude plugin list` reports
`No plugins installed.` The declaration is inert — nothing installs the plugin
on the strength of it. The declaration was therefore removed rather than left
in place asserting a capability the repository does not have.

A caution for anyone tempted to retry it: an early A/B *appeared* to prove it
worked. That run was in a container where `claude plugin install --scope
project` had just populated `~/.claude/plugins/`, so it measured the local
install, not the declaration. Test from clean plugin state or not at all.

#### Delivery decision

- **Supported route** — `dev/cloud/setup-mattpocock-skills.sh` explicitly
  creates a pinned local marketplace, installs the plugin before Claude
  launches, writes the user-level repository configuration pointer, and
  verifies installed state. See `docs/cloud-environment-dev-skills.md`.
- **Disproved repository route** — PR #17 added both an inline
  `extraKnownMarketplaces` declaration and exact `enabledPlugins` entry. Two
  independent fresh cloud sessions still created no marketplace or installed
  plugin and reported `Unknown skill`. Repository declarations do not trigger
  automatic cloud installation on Claude Code 2.1.226.
- **Rejected fallback** — committing the skills to `.claude/skills/`, which
  the docs say cloud sessions do load. It costs namespacing: project skills are
  invoked as `/code-review`, not `/mattpocock-skills:code-review`, and this
  collection ships a `code-review` skill that would then **replace** the bundled
  one. It would also make the skills discoverable to the autonomous loop.

There is no supported local-terminal wrapper. The environment-scoped route does
not change repository discovery and is not used by the GitHub Actions
autonomous loop. Any future route must first identify its caller and preserve
the runner controls below.

## Why the runner's `--allowedTools` is not sufficient on its own

`loop/run_session.sh` passes an `--allowedTools` list that does not name
`Skill`. That is worth being precise about, because the reasoning recorded in
`backlog/BL-0006-scope-agent-deny-rules.md` leans on this flag:

> `run_session.sh` passes an `--allowedTools` **allowlist**, and `git push` is
> not in it, so the unattended agent cannot push regardless of what this file
> says.

That conclusion is correct for `git push`, but for a reason narrower than
"allowlist." Per the Claude Code CLI reference, `--allowedTools` is an
**auto-approve list, not a restricting allowlist** — "tools that execute without
prompting for permission [...] To restrict which tools are available, use
`--tools` instead."

Tools omitted from it remain available and fall back to prompting. On the
autonomous path there is nobody to prompt, so a *permission-gated* tool is
effectively denied — which is why the `Bash`/`Edit`/`Write` reasoning in BL-0006
holds.

The `Skill` tool is not permission-gated. Claude invokes skills without a
permission prompt. So omitting `Skill` from `--allowedTools` does **not** keep
skills away from an autonomous session; if a skill were discoverable, the agent
could invoke it, and its description would sit in the agent's context either
way.

This is why environment separation alone is not treated as the runner's
security boundary. If a future repository-scoped route makes the skills
discoverable, the explicit controls below still have to hold.

## The applied backstop

`loop/run_session.sh` passes two independent controls on the `claude -p`
invocation:

```bash
--disable-slash-commands \
--disallowedTools "Skill" "Read(dev/plugins/**)" \
```

`--disable-slash-commands` disables skills at the feature level.
`--disallowedTools "Skill"` is a bare tool name, which *removes the tool from
Claude's context* outright rather than denying matching calls. Either alone
would do; both are cheap and fail independently.

This costs the loop nothing, because the repository makes no use of the `Skill`
tool on the autonomous path (see above). It converts the guarantee from "the
loop was not handed the flag" into "the loop structurally cannot run a skill" —
including anything a future delivery route makes discoverable, and one someone
later drops into `.claude/skills/` by mistake.

`loop/` is human-owned under ADR-0009; this was applied at the operator's
explicit direction during review, and `tests/test_dev_plugins.py` asserts the
runner still carries both controls.

## What the guarantee is, precisely

These skills are **never listed to the agent, never invokable, and not readable
whole** by an autonomous session. The loop does not inherit the Alpha Lab Dev
plugin or user memory, and the vendored tree remains ordinary repository files.

That last clause is narrower than it may sound, and the difference matters.
`dev/plugins/` holds ordinary files inside the repository. Not passing
`--plugin-dir` means they are never registered as skills and their descriptions
never enter the agent's context — but it does nothing to stop the agent reading
them as prose, and `Read`, `Glob`, and `Grep` are all allowlisted for the
session agent. The scoped `Read(dev/plugins/**)` deny closes the read path.

`Glob` and `Grep` are not covered: an autonomous session can still list paths
under `dev/plugins/` and see lines matching a search. Denying those too would
cost more than it buys — the agent needs `Glob` and `Grep` across the tree, and
permission patterns for them do not scope cleanly by path. So the honest
statement of the boundary is the one above: not loaded, not invokable, not
readable whole. It is not "the autonomous agent cannot know these files exist".

### The read deny was verified behaviourally, not just asserted

A permission pattern that matches nothing fails silently — the flag is present,
the tests pass, and the file is readable anyway. Every documented deny example
uses a `./` prefix (`Read(./secrets/**)`), and the runner's rule is bare
(`Read(dev/plugins/**)`), so it was checked against the real CLI rather than
assumed equivalent:

| Invocation | Outcome |
| :--- | :--- |
| `--allowedTools Read --disallowedTools "Read(dev/plugins/**)"`, asked to read a vendored `SKILL.md` | refused — "I don't have permission to read that file" |
| same prompt, deny flag omitted | read it, returned `# Test-Driven Development` |

The bare relative pattern resolves against the project directory; the `./`
prefix in the documentation examples is a convention, not a requirement. Redo
this A/B if the pattern is ever edited — `tests/test_dev_plugins.py` can only
assert the string is present, not that it matches anything.

## Adding another developer-only plugin

1. Vendor it under `dev/plugins/<name>/` with a `.claude-plugin/plugin.json`.
2. Record provenance in `dev/plugins/<name>/VENDOR.md` — upstream URL, commit
   SHA, version, license, date.
3. Add the pinned source to `dev/cloud/setup-mattpocock-skills.sh`.
4. Update the setup-script digest and mark cloud acceptance pending.
5. Verify fresh and cached Alpha Lab Dev sessions before merge.
6. Run `python -m unittest discover -s tests`.

Review what you vendor. A plugin can ship hooks, MCP servers, and skills that
declare `allowed-tools` to grant themselves tool access without prompting. The
currently vendored collection ships none of those; `tests/test_dev_plugins.py`
checks that this stays true.
