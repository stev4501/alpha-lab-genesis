# BL-0006: Scope the agent deny rules to the runner

- Status: open
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

## Recommendation to evaluate, not to assume

Option 3 matches the actual risk shape: evidence should be immutable to every
automated writer regardless of supervision, whereas loop machinery is precisely
what a supervised human-plus-assistant session exists to repair.

One concrete narrowing is worth considering on its own, independent of which
option is chosen. During the 2026-08-08 session the `Bash(git push *)` deny
blocked a supervised session from pushing a documentation-only commit to a
feature branch four times, which is friction with no corresponding protection:
`main` is already defended server-side by the `main history protection`
ruleset, which no client-side rule can strengthen. Narrowing the deny to
`main` and the force variants would leave every protection intact — the runner
still cannot push `main`, and the ruleset still refuses force-pushes from
anyone — while letting a supervised session finish its own work.

Option 1 remains the correct default for `Edit`/`Write` on `loop/`,
`evaluator/`, and `scripts/`: the patch handoff cost about two minutes, and the
friction falls exactly on the changes that deserve it.

## Definition of done

A decision is recorded in a journal entry and, if anything changes, ADR-0008's
"Enforcement reality" section is updated to describe which layer constrains
which kind of session.
