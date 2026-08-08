# CCR 2026-08-08: keep vendored dev skills off the autonomous path

- Origin: supervised session, 2026-08-08, while vendoring the `mattpocock-skills`
  plugin for developer use
- Requires sealed changes: no
- Requires protected-path changes: yes (`loop/`, and optionally `.claude/`) —
  human applies
- Related: `backlog/BL-0006-scope-agent-deny-rules.md`, `docs/dev-only-skills.md`

## What was done without touching protected paths

The plugin is vendored at `dev/plugins/mattpocock-skills/` (25 skills, upstream
commit `84fdeff`, MIT). That path is not a Claude Code discovery path at any
level, so nothing loads it implicitly. `bin/dev-session` starts a supervised
session with `--plugin-dir` pointing at it; `loop/run_session.sh` passes no
plugin flag, so autonomous sessions load nothing.

`tests/test_dev_plugins.py` asserts the invariants that keep it that way:
`.claude/skills/` does not exist, `.claude/settings.json` declares no
`enabledPlugins`, `run_session.sh` passes no `--plugin-dir`/`--plugin-url`,
no nested `.claude/` tree exists under `dev/plugins/`, and no vendored skill
ships hooks, MCP servers, `allowed-tools`, or executables.

That is sufficient for the requirement. The rest of this request is about
turning one convention into an enforced control.

## Part A — recommended: remove the `Skill` tool from the session agent

**Patch:** `core_change_requests/patches/2026-08-08-a-skill-backstop.diff`
(verified with `git apply --check`)

Adds `--disallowedTools "Skill"` to the `claude -p` invocation, plus a comment
recording why.

### Why the current `--allowedTools` list does not already cover this

`run_session.sh` does not name `Skill` in `--allowedTools`, which looks like it
should be enough. It is not, and the reason matters beyond this change request
because `BL-0006` reasons from the same flag:

> `run_session.sh` passes an `--allowedTools` **allowlist**, and `git push` is
> not in it, so the unattended agent cannot push regardless of what this file
> says.

The conclusion about `git push` is right; the mechanism is narrower than
"allowlist". Per the Claude Code CLI reference, `--allowedTools` is an
**auto-approve list, not a restricting allowlist** — "tools that execute without
prompting for permission [...] To restrict which tools are available, use
`--tools` instead."

Omitted tools remain available and fall back to prompting. On the unattended
path nobody can answer a prompt, so a *permission-gated* tool is effectively
denied. `Bash`, `Edit`, and `Write` are permission-gated, so BL-0006's
conclusion holds for `git push`.

`Skill` is not permission-gated — Claude invokes skills without a prompt. So
omitting it from `--allowedTools` does not keep skills away from the session
agent, and a discoverable skill's description would occupy the agent's context
regardless of whether it were ever invoked.

Nothing is discoverable today, so this is a latent gap rather than a live hole.
It becomes live the moment anyone adds `.claude/skills/`, sets `enabledPlugins`,
or installs a user-level plugin on a machine that runs `run_session.sh` locally.

### Why it costs the loop nothing

This repository's nine core skills live at `skills/<name>/SKILL.md` — repo root,
which is not a Claude Code discovery path. They are never registered as Claude
Code skills; `loop/prompts/session.md` directs the agent to read them, and it
does so with `Read`. The autonomous path makes no use of the `Skill` tool at
all, so removing it changes no current behaviour.

### Suggested follow-up

If Part A is applied, add to `tests/test_dev_plugins.py`:

```python
def test_runner_removes_the_skill_tool(self):
    runner = (ROOT / "loop" / "run_session.sh").read_text(encoding="utf-8")
    self.assertIn('--disallowedTools "Skill"', runner)
```

It is deliberately omitted for now: the test would be red until the patch lands,
and a red suite flips the next session into maintenance mode.

## Part B — optional: protect `dev/` and `bin/`

**Patch:** `core_change_requests/patches/2026-08-08-b-protect-dev-bin.diff`
(verified with `git apply --check`)

Adds `dev/` and `bin/` to the `PROTECTED` regex in `validate_session.sh` and to
the hard-rules lists in both loop prompts.

Today `dev/plugins/` and `bin/` are agent-space: an autonomous session could
rewrite a vendored skill body or the session wrapper. It cannot *load* those
skills, so this is not an escape route — but editing third-party vendored code
and developer tooling is outside the mandate in `session.md`, and the vendored
tree is exactly the kind of content that should change only under review.

If Part B is applied, the deny rules must move in lockstep or the failure mode
gets worse rather than better. `validate_session.sh` rejects the branch *after*
the session has spent its budget; the `.claude/settings.json` deny rules stop
the edit at the point of the attempt. Every other protected path in this repo
appears in both. Add to `.claude/settings.json`:

```json
"Edit(dev/**)",
"Write(dev/**)",
"Edit(bin/**)",
"Write(bin/**)"
```

Applying the `validate_session.sh` half alone would let a session burn 90
minutes and then fail the gate for a change it was never warned off. Apply both
halves or neither.

## Interaction with the pending PR-mode patches

`core_change_requests/2026-08-08-pr-mode-loop.md` (merged to main in #4) also
carries an unapplied patch against `loop/run_session.sh`. Both are pending at
the same time, so the composition was tested rather than assumed.

They touch disjoint regions. The PR-mode runner patch has hunks at original
lines 2, 16, 32, 98, and 130; Part A's are at 68 and 77, in the `claude -p`
invocation the PR-mode patch does not modify. Verified in both orders against
`main` at `016d4f9`:

| Order | Result |
| :--- | :--- |
| PR-mode, then Part A | applies, hunks offset +25 |
| Part A, then PR-mode | applies, hunks offset +12 |

In both cases the composed script parses under `bash -n` and carries exactly one
`--disallowedTools "Skill"`, positioned directly after `--allowedTools`. No
ordering constraint; apply them in either order.

## How to apply

```bash
git apply core_change_requests/patches/2026-08-08-a-skill-backstop.diff
# optional, with the settings.json edit above:
git apply core_change_requests/patches/2026-08-08-b-protect-dev-bin.diff

bash -n loop/run_session.sh && bash -n loop/validate_session.sh
python scripts/validate_repository.py
python -m unittest discover -s tests
```

`git apply` reports "Hunk N succeeded at M (offset X lines)" when the PR-mode
patch has already landed. That is expected, not a warning to act on.

## What is blocked until this is applied

Nothing. Part A hardens a layer; Part B narrows write access. The
developer-only arrangement works as delivered.
