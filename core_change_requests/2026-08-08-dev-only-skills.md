# CCR 2026-08-08: keep vendored dev skills off the autonomous path

- Origin: supervised session, 2026-08-08, while vendoring the `mattpocock-skills`
  plugin for developer use
- Requires sealed changes: no
- Requires protected-path changes: yes — Part A touches `loop/`; Part B also
  touches `.claude/` and `CODEOWNERS`, and amends ADR-0009's ownership
  enumeration. Human applies.
- Related: `backlog/BL-0006-scope-agent-deny-rules.md`, `docs/adr/0009-agent-owned-operations.md`,
  `docs/dev-only-skills.md`

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
(verified with `git apply --check`) — covers `validate_session.sh`, both loop
prompts, `.claude/settings.json`, and `CODEOWNERS` in one commit.

Today `dev/plugins/` and `bin/` are agent-space: an autonomous session could
rewrite a vendored skill body or the session wrapper. It cannot *load* those
skills, so this is not an escape route — but editing third-party vendored code
and developer tooling is outside the mandate in `session.md`, and the vendored
tree is exactly the kind of content that should change only under review.

ADR-0009 sharpens this both ways. It removes the pull-request gate, so session
output now reaches `main` with no human reading the diff — which is the argument
*for* protecting a vendored third-party tree. But it also enumerates the
human-owned set precisely, and `dev/` and `bin/` are not in it:

> Sealed components (`evaluator/`, `scripts/`, `schemas/`, `CORE_MANIFEST.json`),
> the loop machinery and protections (`loop/`, `.github/`, `.claude/`,
> `CODEOWNERS`, `MISSION.md`, `CONTEXT.md`), generation changes (G-XXXX), and
> freeze tags move only by human hands after explicit approval.

**So Part B amends ADR-0009's enumeration.** That is a governance decision, not
a regex tweak, and it should be taken as one — an ADR amendment or a recorded
journal decision, the same way ADR-0009 recorded its own. If the answer is that
vendored dev tooling is neither core nor the agent's forward motion and should
simply not live under a protected path, dropping Part B and leaving `dev/` in
agent-space is a coherent alternative. Part A does not depend on it.

### All four surfaces move together

An earlier revision of this request said protected paths appear in "both" the
validator and the deny rules. That was wrong: every machinery path in this repo
(`evaluator/`, `scripts/`, `schemas/`, `loop/`, `.github/`, `.claude/`) appears
in **three** places, and ADR-0009 names `CODEOWNERS` as human-owned itself.
Applying only some of them leaves `dev/` and `bin/` inconsistent with every
other protected path:

| Surface | Effect if omitted |
| :--- | :--- |
| `.claude/settings.json` deny | agent attempts the edit; nothing stops it at the point of the attempt |
| `loop/validate_session.sh` | the branch is not rejected at the gate |
| `loop/prompts/*.md` | the agent is never told the path is off-limits |
| `CODEOWNERS` | no review is requested on the path |

The rebuilt patch covers all four in one commit, so this is now apply-or-don't
rather than a sequence to get right by hand. The worst outcome — validator
without deny rules — would let a session burn 90 minutes and then fail the gate
for a change it was never warned off.

Note that under ADR-0009 the validator runs only from `run_session.sh` inside
the runner: the pending rescind patch deletes `.github/workflows/session-validate.yml`,
so there is no CI copy of the gate once it is applied. Part B's enforcement is
runner-side and prompt-side only.

## Part A applies in either PR-mode state

`loop/run_session.sh` has moved twice under this request. PR-mode landed in #5
(`8906f4f`), rewriting 93 lines; ADR-0009 then rescinded BL-0005 and left
`patches/2026-08-09-rescind-pr-mode.diff` pending, which reverts it. Part A
targets the `claude -p` invocation, which both states leave structurally
intact, so it was tested against both rather than pinned to one:

| Runner state | Part A result |
| :--- | :--- |
| PR-mode applied (current `main`) | applies exactly, hunks at 93 and 113 |
| Rescind patch applied first | applies, hunks offset −25, back at 68 and 88 |

Both parse under `bash -n` and yield exactly one `--disallowedTools "Skill"`
directly after `--allowedTools`. **Apply Part A before or after the rescind
patch; no regeneration needed either way.** `git apply` prints "Hunk N
succeeded at M (offset −25 lines)" in the post-rescind case — expected, not a
warning to act on.

### ADR-0009 raises the stakes on the finding above

ADR-0009 supersedes ADR-0008's "Enforcement reality" and names three layers.
The second is:

> **Runner-side, binding on the unattended agent:** the `--allowedTools`
> allowlist, the `.claude/settings.json` deny rules, and the validator executed
> from `main`'s copy rather than the branch under test. [...] That is no longer
> an accepted MVP deficiency awaiting closure. It is the design.

That promotes `--allowedTools` from an incidental flag to one of three
deliberate enforcement layers. The finding in this request is a caveat on
exactly that layer, and it is worth stating in the ADR's own terms:
`--allowedTools` binds the unattended agent **for permission-gated tools only**.
`Bash`, `Edit`, and `Write` are permission-gated, so the layer does the work the
ADR assigns it for every tool the runner currently reasons about. It does not
bind tools that execute without a permission prompt, and `Skill` is one.

This does not weaken ADR-0009's decision — the split of ownership stands on its
own reasoning. It means the runner-side layer needs `--disallowedTools` to
cover the non-gated class, which is what Part A adds. If the enforcement-by-
layer section is ever restated, "the `--allowedTools` allowlist" is more
accurate as "the `--allowedTools` allowlist and `--disallowedTools` removals".

`BL-0006`'s 2026-08-09 note records that the push-deny enumeration keeps its
guardrail job indefinitely now that no server-side boundary is coming. The
distinction that note draws — guardrail versus boundary — is the same one at
work here, applied to a different flag.

## How to apply

```bash
git apply core_change_requests/patches/2026-08-08-a-skill-backstop.diff
# optional — self-contained, no manual settings.json edit needed:
git apply core_change_requests/patches/2026-08-08-b-protect-dev-bin.diff

bash -n loop/run_session.sh && bash -n loop/validate_session.sh
python scripts/validate_repository.py
python -m unittest discover -s tests
```

Part A applies against `main` with or without the pending rescind patch; see
the table above for which offsets to expect. Part B applies exactly.

## What is blocked until this is applied

Nothing. Part A hardens a layer; Part B narrows write access. The
developer-only arrangement works as delivered.
