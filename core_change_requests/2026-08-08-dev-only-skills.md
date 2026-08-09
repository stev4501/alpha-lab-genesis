# CCR 2026-08-08: keep vendored dev skills off the autonomous path

- Origin: supervised session, 2026-08-08, while vendoring the `mattpocock-skills`
  plugin for developer use
- Requires sealed changes: no
- Status: **Part A applied** to `loop/run_session.sh` on 2026-08-09 at the
  operator's explicit direction during review of PR #3. **Part B is blocked**
  pending an explicit ADR-0009 amendment — do not apply it before then.
- Requires protected-path changes: Part A touched `loop/` (done); Part B would
  touch `loop/`, `.claude/`, and `CODEOWNERS`.
- Related: `backlog/BL-0006-scope-agent-deny-rules.md`, `docs/adr/0009-agent-owned-operations.md`,
  `docs/dev-only-skills.md`

## What was done without touching protected paths

The plugin is vendored at `dev/plugins/mattpocock-skills/` (25 skills, upstream
commit `84fdeff`, MIT). That path is not a Claude Code discovery path at any
level, so nothing loads it implicitly. `bin/dev-session` starts a supervised
session with `--plugin-dir` pointing at it; `loop/run_session.sh` passes no
plugin flag, so autonomous sessions never load them as skills. The runner also
denies `Read(dev/plugins/**)`, so they do not enter context as prose either;
`Glob` and `Grep` can still surface paths and matching lines. The guarantee is
"never loaded as skills, never invokable, not readable whole" — see
`docs/dev-only-skills.md`.

**Note 2026-08-09:** `--plugin-dir` cannot reach cloud or web sessions, so these
skills are unavailable there. Declaring the plugin in `.claude/settings.json`
was tried and disproved by a cloud-session probe — the declaration installs
nothing — and was removed rather than left asserting a capability the repository
does not have. See `docs/dev-only-skills.md` for the evidence and the remaining
options.

`tests/test_dev_plugins.py` asserts the invariants that keep it that way:
`.claude/skills/` does not exist, a declared `enabledPlugins` is accompanied by
the runner controls, `run_session.sh` passes no `--plugin-dir`/`--plugin-url`,
no nested `.claude/` tree exists under `dev/plugins/`, and no vendored skill
ships hooks, MCP servers, `allowed-tools`, or executables.

That is sufficient for the requirement. The rest of this request is about
turning one convention into an enforced control.

## Part A — APPLIED: remove skills from the session agent

Applied directly to `loop/run_session.sh`. The patch file
`patches/2026-08-08-a-skill-backstop.diff` was regenerated to match exactly what
landed and is retained as the record, the same way the PR-mode request retains
its applied patches. Do not re-apply it.

Two independent controls on the `claude -p` invocation:

```bash
--disable-slash-commands \
--disallowedTools "Skill" "Read(dev/plugins/**)" \
```

`--disable-slash-commands` disables skills at the feature level (confirmed in
Claude Code 2.1.226: "Disable all skills"). `--disallowedTools "Skill"` is a
bare tool name, which removes the tool from the agent's context outright. Either
alone would do; both are cheap and fail independently. The scoped
`Read(dev/plugins/**)` deny keeps the vendored tree out of context as prose.

`tests/test_dev_plugins.py` asserts all three, reading the runner with comment
lines stripped so a comment mentioning a flag can neither satisfy nor break the
assertion.

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

This remains a latent gap rather than a live hole, because nothing declares
these skills to any session. It stops being latent the moment a delivery route
for cloud sessions is found — any route that reaches them also reaches the loop
— so the controls below are what would carry the weight, not this flag.

### Why it costs the loop nothing

This repository's nine core skills live at `skills/<name>/SKILL.md` — repo root,
which is not a Claude Code discovery path. They are never registered as Claude
Code skills; `loop/prompts/session.md` directs the agent to read them, and it
does so with `Read`. The autonomous path makes no use of the `Skill` tool at
all, so removing it changes no current behaviour.

## Part B — BLOCKED pending an ADR-0009 amendment

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
the runner. The rescind landed on `main` in `0cbb3e2` and deleted
`.github/workflows/session-validate.yml`, so there is no CI copy of the gate at
all now. Part B's enforcement would be runner-side and prompt-side only.

## The rescind landed; the controls survived

`patches/2026-08-09-rescind-pr-mode.diff` was applied to `main` in `0cbb3e2`,
reverting the PR-mode runner and deleting the `session-validate` workflow. That
commit and Part A both rewrite `loop/run_session.sh`, so the interaction was
predicted, tested ahead of time, and then confirmed on the real merge:

| Check | Result |
| :--- | :--- |
| merge of `main` into this branch | auto-merged, no conflict |
| PR-mode remnants in the runner | none — `gh pr create` and `open_pull_request` gone, direct push to `main` restored |
| both skill controls | present, still directly after `--allowedTools` |
| `bash -n loop/run_session.sh` | parses |
| `tests/test_dev_plugins.py` | green |

A clean auto-merge is not by itself evidence the result is right, which is why
each line above was checked rather than inferred from git's exit code. The
record patch in `patches/` was regenerated against post-rescind `main` and
reverses cleanly against the tree.

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

## Verifying what is applied

Part A is applied; its patch file is a record, not a step. Do not run
`git apply` on it — it will fail, because the tree already contains the change.
To confirm the tree matches the record:

```bash
git apply --check --reverse core_change_requests/patches/2026-08-08-a-skill-backstop.diff
bash -n loop/run_session.sh && bash -n bin/dev-session
python scripts/validate_repository.py
python -m unittest discover -s tests
```

Part B is **not** applied and must not be until ADR-0009 is amended (see above).
When that decision is recorded, it applies with:

```bash
git apply core_change_requests/patches/2026-08-08-b-protect-dev-bin.diff
```

The permission rule `Read(dev/plugins/**)` cannot be checked by any of the
commands above — a pattern that matches nothing passes every one of them. It
was verified by A/B against the live CLI; `docs/dev-only-skills.md` records the
method and result, and that A/B should be redone if the pattern is ever edited.

## Status

Part A is applied and enforced by tests. Part B is blocked on a governance
decision, not on any technical work. Nothing else in this request is
outstanding, and the developer-only arrangement works as delivered.
