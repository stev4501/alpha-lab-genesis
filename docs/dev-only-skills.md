# Developer-only skills

How third-party Claude Code skills are made available to humans working in this
repository without becoming usable by the autonomous research sessions launched
by `loop/run_session.sh`.

As things stand nothing declares these skills to any session, so the loop does
not load them at all. The runner controls are kept regardless: they are what
would hold if a future delivery route made the skills discoverable, and they
were verified against a session that had them installed.

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
discovery path at any level. It is loaded per-session with an explicit flag:

```bash
bin/dev-session
# == claude --plugin-dir dev/plugins/mattpocock-skills \
#           --append-system-prompt-file docs/agents/session-prompt.md
```

Both flags matter. `--plugin-dir` loads the skills; the second points them at
their per-repo configuration in `docs/agents/`, which most of them expect to
"have been provided" without naming a path. See `docs/agents/README.md`.

`loop/run_session.sh` passes no `--plugin-dir`. Plugin skills are namespaced —
`/mattpocock-skills:tdd` — so they cannot shadow a core skill or the bundled
`/code-review`.

### Cloud and web sessions: environment-scoped delivery

`--plugin-dir` only works where you control the launch — a local terminal.
Claude Code on the web and other cloud sessions are launched by the harness, so
the flag cannot be injected. Repository plugin declarations were tried and
disproved, but the dedicated **Alpha Lab Dev** cloud environment now installs
the pinned plugin explicitly before Claude launches. First-session direct and
subagent invocation and second-session cached reuse are verified in
`.claude/cloud-environment-plugin-acceptance.json`.

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

#### Current delivery routes

- **Local terminal** — `bin/dev-session`, which works. For persistence outside
  this repo, `claude plugin install mattpocock-skills` at user scope.
- **Disproved repository route** — PR #17 added both an inline
  `extraKnownMarketplaces` declaration and exact `enabledPlugins` entry. Two
  independent fresh cloud sessions still created no marketplace or installed
  plugin and reported `Unknown skill`. Repository declarations do not trigger
  automatic cloud installation on Claude Code 2.1.226.
- **Cloud environment installation** — `dev/cloud/setup-mattpocock-skills.sh`
  explicitly creates a pinned local marketplace, installs the plugin before
  Claude launches, and verifies the installed SHA and enabled state. See
  `docs/cloud-environment-dev-skills.md`. This is environment-scoped rather than
  repository-scoped; fresh and cached cloud acceptance are verified.
- **Documented fallback** — committing the skills to `.claude/skills/`, which
  the docs say cloud sessions do load. It costs namespacing: project skills are
  invoked as `/code-review`, not `/mattpocock-skills:code-review`, and this
  collection ships a `code-review` skill that would then **replace** the bundled
  one. Renaming the directory avoids that. Not done; it is a decision, not a
  drop-in.

The environment-scoped route does not change repository discovery and is not
used by the GitHub Actions autonomous loop. Any future repository-scoped route
would still reach the loop and must preserve the runner controls below.

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

This is a gap in a layer rather than an active hole today, because nothing
declares these skills to any session. It stops being latent the moment a
delivery route is found — any route that reaches cloud sessions also reaches the
loop — so the explicit controls below are what hold, not this flag.

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
whole** by an autonomous session — whether they arrive via the declared plugin
or the vendored tree.

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

## What the wrapper refuses

`bin/dev-session` exits 2 on selected explicit print, background, and cloud
flag forms. The guard matches wider than the literal flags, and the reason
is worth recording: Claude Code accepts **clustered short flags**, so `-pd` and
`-dp` engage `--print` exactly as `-p` does. An exact-match guard on `-p` and
`--print` looks correct and misses every cluster — which is what the first
version of this wrapper did.

Print mode also turned out not to be the only route to an unattended session,
so the guard covers a class rather than a flag.

| Form | Wrapper | Why |
| :--- | :--- | :--- |
| `-p`, `--print` | refused | print / non-interactive mode |
| `-pd`, `-dp`, `-pv` | refused | clustered short flags engage `--print` too |
| `--print=true` | refused | the CLI also rejects it as an unknown option |
| `--bg`, `--background` | refused | "Start the session as a background agent" — runs locally, plugin loaded, nobody watching |
| `--cloud`, `--remote` | refused | cloud session and its deprecated alias; precaution, see below |
| `--remote-control`, `--rc` | passed | documented as starting an *interactive* session, driven by a human elsewhere |
| `--permission-mode`, `--model`, `-d`, `-c`, `-w`, `--add-dir`, `--agent` | passed | ordinary interactive flags |
| `--bg` etc. **after** `--` | refused | Claude Code does not honour the marker here — see below |
| a positional prompt mentioning `-p` or `--bg` | passed | not a flag |

Long flags are exempted before the cluster test, so `--permission-mode` is not
caught by its leading `p`. `--input-format` needs no rule: the CLI documents it
as only working with `--print`, which is already refused.

### `--` is not honoured, because Claude Code does not honour it

Scanning deliberately continues past the `--` end-of-options marker. This looks
wrong — conventionally `--` means "everything after this is positional" — and an
earlier revision of this wrapper implemented exactly that, on that assumption.

The assumption is false here. Against Claude Code 2.1.226:

```bash
claude --plugin-dir "$PWD/dev/plugins/mattpocock-skills" -- --bg
# → Starting background service…
# → backgrounded · <id>
```

`--bg` is still acted on after the marker, so a wrapper that stopped scanning at
`--` would hand back the exact bypass the guard exists to close. The cost is
that `dev-session -- --bg` refuses a prompt that merely mentions `--bg`; a
developer who wants to discuss the flag can quote it differently, and that is
the cheaper side of the trade.

### Version-pinned compatibility check

The unit tests run against a stubbed `CLAUDE_BIN` and therefore **cannot** prove
anything about Claude's parser. Two behaviours the wrapper depends on are
properties of the CLI, not of this repository, and need re-checking whenever
Claude Code is upgraded:

```bash
# 1. Does `--` still fail to end option parsing?  (expect: background session starts)
npx -y @anthropic-ai/claude-code@<version> \
  --plugin-dir "$PWD/dev/plugins/mattpocock-skills" -- --bg

# 2. Do clustered short flags still engage --print?  (expect: the --print prompt error)
npx -y @anthropic-ai/claude-code@<version> -pd "say ok"
```

Check 1 **starts a real background session**. Stop it immediately:

```bash
claude agents --json          # find the id and pid
kill <pid>
```

Last verified against **2.1.226**: both behaviours confirmed. If a future
version starts honouring `--`, drop the note above, stop `first_refusal` at the
marker in `bin/dev-session`, and reverse
`TestRefusalRules.test_end_of_options_marker_does_not_stop_the_scan` in
`tests/test_dev_session.py`.

### `claude --help` is not the authoritative flag surface

Worth knowing before extending the list: `--remote` and `--rc` are both
recognized by the CLI and neither appears in `--help`. An enumeration of help
output looks exhaustive and is not — which is how `--remote` survived a pass
that was specifically hunting for this class of flag.

To test whether a candidate flag exists without triggering its side effects,
exploit the fact that the parser names the **first** unknown option:

```bash
claude <candidate> --print=true
```

If the error names `<candidate>`, it is not a real flag. If it names
`--print=true`, the candidate was accepted. This is how `--remote`, `--rc`, and
a dozen speculative aliases (`--headless`, `--detach`, `--daemon`, `--batch`,
…) were checked without creating a single background or cloud session.

`--cloud` is refused on precaution rather than a demonstrated bypass. Whether
`--plugin-dir` survives into a cloud container was not verified, and creating
one to find out has side effects. The asymmetry decides it: refusing costs a
developer one direct `claude` invocation, while being wrong the other way puts
these skills in an unattended session.

A blanket TTY requirement was considered and rejected. Claude Code documents
`-p` as print mode and does not document redirected streams as activating it,
so a TTY gate would break legitimate terminal wrappers without closing any hole
the rules above miss.

`tests/test_dev_session.py` covers both directions — every refused form above
and every allowed one, asserted against the rules directly rather than through
a subprocess. A guard that refused everything would otherwise pass a
refusal-only test while breaking the only supported way to use these skills.

`bin/dev-session` is a small Python script rather than a shell wrapper. It
started as three lines of bash; by the time it had a flag-class guard, a config
pointer, and its own failure modes, every assertion about it had to go through a
stubbed subprocess. As Python its rules are importable, which is what lets the
flag table be exhaustive instead of representative.

The rewrite was raised as a judgement call and directed by the operator, not
taken on the implementer's initiative — the accretion was flagged, and the
answer was to make it a script with its own tests. Recorded here because the
diff on its own looks like scope that arrived without being asked for.

This is a guardrail, not a boundary, and the distinction is load-bearing. The
wrapper rejects **selected explicit print, background, and cloud flag forms** —
it is not a general "interactive only" gate and does not claim to be. Claude
Code 2.1.226 also treats non-TTY stdout as non-interactive, and the flag surface
has not proven enumerable: four bypasses were found across three review rounds,
including a `--remote` alias absent from `claude --help`. TTY enforcement,
`ultrareview`-style workflows, and exhaustive alias discovery are accepted
trade-offs here, not solved problems.

What actually keeps these skills away from the autonomous loop is runner-side
and does not involve this wrapper at all: `loop/run_session.sh` never invokes
it, passes no `--plugin-dir`, and supplies `--disable-slash-commands` and
`--disallowedTools "Skill" "Read(dev/plugins/**)"`. No wrapper bypass reaches
the loop, because the loop never calls the wrapper.

## Adding another developer-only plugin

1. Vendor it under `dev/plugins/<name>/` with a `.claude-plugin/plugin.json`.
2. Record provenance in `dev/plugins/<name>/VENDOR.md` — upstream URL, commit
   SHA, version, license, date.
3. Add the path to `PLUGIN_DIRS` in `bin/dev-session`.
4. Run `python -m unittest discover -s tests`.

Review what you vendor. A plugin can ship hooks, MCP servers, and skills that
declare `allowed-tools` to grant themselves tool access without prompting. The
currently vendored collection ships none of those; `tests/test_dev_plugins.py`
checks that this stays true.
