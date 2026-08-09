# BL-0006: Scope the agent deny rules to the runner

- Status: **closed 2026-08-09** — option 3 decided by the operator and applied
  (see "Decided 2026-08-09" below)
- Priority: 6
- Requires sealed changes: no
- Requires protected-path changes: yes (`loop/`, `.claude/`) — human applies
- Origin: observed directly while implementing the BL-0005 sibling fixes,
  2026-08-08

## The observation

`.claude/settings.json` denies `Edit`/`Write` on `loop/**`, `.claude/**`,
`.github/**`, `evaluator/**`, `scripts/**`, `schemas/**`, and the protected
root files. Those rules were written for the unattended session agent the
runner launches with `claude -p`.

But project settings apply to **every** Claude Code session opened in this
repository, including human-supervised maintenance sessions. During the
2026-08-08 supervised session this blocked the assistant from applying agreed
fixes to `loop/run_session.sh`; the fixes had to be handed to the human as a
patch instead.

That outcome is not wrong — a human applying protected-path changes is exactly
the governance model ADR-0008 describes, and the deny rule doing its job to an
assistant working under supervision is evidence the control is real, not
decorative. But it is worth deciding deliberately rather than inheriting by
accident, because the current arrangement makes the supervised path for
repairing the loop strictly more awkward than the unsupervised path for
running it.

## Options

1. **Keep as is.** Every protected-path change goes through a human hand
   applying a patch. Maximum friction, maximum assurance, and the friction
   falls on exactly the changes that deserve it. Costs nothing to choose.
2. **Move the restrictions to the runner.** Put the deny list in
   `loop/agent-settings.json` and have `run_session.sh` pass it explicitly to
   the `-p` invocation, leaving `.claude/settings.json` minimal. The
   unattended agent stays fully constrained; supervised sessions are governed
   by the human present. Note the trade: the deny list stops being a repo-wide
   default, so any future automation that forgets the flag is unconstrained.
3. **Split by intent.** Keep evidence paths (`results/`, `reviews/`,
   `data/snapshots/`, `data/raw/`, `data/provenance/`) denied repo-wide for
   everyone including supervised sessions, and move only the machinery paths
   (`loop/`, `.github/`, `.claude/`) to the runner-scoped file.

## What the deny list does not cover

Worth recording before it is rediscovered: the deny rules constrain the `Bash`,
`Edit`, and `Write` tools. They do not constrain MCP tools. A session with a
GitHub MCP server connected can write repository contents over the API without
touching a denied pattern.

This is not a runner risk — `run_session.sh` passes an explicit
`--allowedTools` allowlist that contains no MCP tools, so the unattended agent
cannot reach them. It applies to supervised sessions, where a human is present
and the API path is a legitimate tool rather than an evasion. The point of
recording it is that the deny list should not be mistaken for a complete
boundary: it is one layer, and the layer that actually binds without
supervision is the runner's allowlist.

This item's own history is the worked example: the commit that added this
section could not be pushed by the supervised session, and reached the
repository through the GitHub API instead, with the human's explicit
authorization. The API path was available the whole time; what made it
legitimate was being asked for, not being reachable.

## Applied 2026-08-08: the push deny, narrowed

The blanket `Bash(git push *)` / `Bash(git push)` pair was replaced with an
enumeration of the forms that target `main`, plus the force variants. Two
reasons:

1. It was protecting nothing on the autonomous path. `run_session.sh` passes
   an `--allowedTools` **allowlist**, and `git push` is not in it, so the
   unattended agent cannot push regardless of what this file says. The deny's
   only effect was on supervised sessions.
2. Its cost was real: it blocked a supervised session from pushing a
   documentation-only commit to a feature branch four times in one session.

Be clear-eyed about what the replacement is. Permission rules support only
exact match and prefix wildcard — there is no mid-command matching — so a
single rule cannot express "any push to `main`". `git push origin  main` with
two spaces, or `git push origin refs/heads/main`, are not caught. It is a
guardrail against a slip, not a boundary, and anyone treating it as a boundary
would be making exactly the mistake this item exists to prevent.

The real boundary for `main` arrives with BL-0005: once the ruleset requires a
pull request, the server refuses every direct push regardless of spelling, and
this enumeration should be deleted rather than maintained.

**Note 2026-08-09:** BL-0005 was rescinded by ADR-0009 — no server-side push
boundary is coming, ever, by decision. The paragraph above is therefore moot:
the enumeration keeps its job as a supervised-session guardrail indefinitely,
and anyone tempted to treat it as a boundary should reread the paragraph
before it. The scoping decision (options 1–3) this item exists for remains
open and is unaffected.

## Recommendation to evaluate, not to assume

Option 3 matches the actual risk shape: evidence should be immutable to every
automated writer regardless of supervision, whereas loop machinery is precisely
what a supervised human-plus-assistant session exists to repair.

Option 1 remains the correct default for `Edit`/`Write` on `loop/`,
`evaluator/`, and `scripts/`: the patch handoff cost about two minutes, and the
friction falls exactly on the changes that deserve it.

## Decided 2026-08-09: option 3, applied

The operator decided it directly, in a supervised session, in these terms: the
agent operating inside the GitHub Action should avoid altering the core; a human
working in the repository with an agent should not be subject to that rule.
That is option 3.

**What moved to `loop/agent-settings.json`**, passed to the unattended agent
with `--settings`: `evaluator/`, `scripts/`, `schemas/`, `loop/`, `.github/`,
`.claude/`, `CORE_MANIFEST.json`, `MISSION.md`, `CONTEXT.md`, `CODEOWNERS`, and
the network/install denies (`curl`, `wget`, `pip install`, `npm`).

**What stayed in `.claude/settings.json`**, binding every session in this
repository: `results/`, `reviews/`, `data/snapshots|raw|provenance/`, and the
`main`/history guardrails narrowed on 2026-08-08. Recorded evidence should be
immutable to any automated writer regardless of supervision; that property has
nothing to do with who is watching.

Three things about the shape of the applied change, since option 2's stated
trade — "any future automation that forgets the flag is unconstrained" — applies
to option 3 equally:

1. `loop/agent-settings.json` restates the repo-wide rules rather than relying
   on the union of settings sources. It does not need to; it does so that
   trimming `.claude/settings.json` in a later session cannot silently loosen
   the unattended path. `tests/test_agent_settings.py` fails if the runner's
   file ever stops being a superset.
2. `run_session.sh` treats a missing or unparseable settings file as fatal in
   preflight rather than running the session anyway. Tested behaviourally
   against a scratch repository, with a positive control, because "the runner
   refuses" is the whole point of the check.
3. A test derives check 1's protected-path regex out of
   `loop/validate_session.sh` and asserts every path in it has a matching deny.
   A path added to the gate but not to the rules would otherwise cost a session
   ninety minutes and then fail validation.

**Against the recommendation below.** That section argued option 1 was the
correct default for `loop/`, `evaluator/`, and `scripts/`, on the grounds that
the patch handoff costs about two minutes and the friction falls on changes that
deserve it. The operator weighed it and chose otherwise; the two-minute estimate
also understates it — this session's own attempt to apply the change was refused
by the rules it was changing, and the work reached the branch through the GitHub
API instead, exactly as the section below describes happening on 2026-08-08.
The argument is left standing rather than rewritten, because it is the reason
the evidence paths did not move.

## Definition of done

A decision on the scoping question (options 1–3) is recorded in a journal entry
and, if anything changes, ADR-0008's "Enforcement reality" section is updated to
describe which layer constrains which kind of session.

**Done 2026-08-09.** Journal: `journals/2026-08-09-deny-rule-scoping.md`.
ADR-0008's "Enforcement reality" was superseded by ADR-0009's "Enforcement,
honestly, by layer" before this decision landed, so the amendment is recorded
there instead.
