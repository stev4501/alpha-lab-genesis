# Issue tracker: GitHub

Issues and specs for human-directed work in this repo live as GitHub issues on
`stev4501/alpha-lab-genesis`.

## Scope: this repo has two work queues, and this file describes one of them

| Queue | Who uses it | Where |
| :--- | :--- | :--- |
| GitHub issues | the human operator, and skills run on their behalf | `stev4501/alpha-lab-genesis` issues |
| `backlog/BL-XXXX-*.md` | the autonomous research loop | files in `backlog/` |

`loop/prompts/session.md` directs the autonomous agent to select the
highest-priority open item from `backlog/`, escalate anything touching a
protected path to `core_change_requests/`, and record what happened in
`journals/<session>.md` plus a rewritten `HANDOFF.md`. `FAILURES.md` is read
during orientation for open blockers, not written as the reporting channel. The
agent never reads GitHub issues, has no allowlisted tool that could, and cannot
invoke these skills at all.

So: **do not migrate `backlog/` into GitHub issues, and do not file agent work
as GitHub issues.** The two queues are deliberate, not an accident to tidy up.

## Reaching GitHub

Which tool depends on where the session runs.

- **Local terminal** — the `gh` CLI, as below. It infers the repo from
  `git remote -v` when run inside a clone.
- **Cloud and web sessions** — `gh` is **not installed**. Use the GitHub MCP
  tools (`mcp__github__*`) instead: `issue_read`, `issue_write`,
  `add_issue_comment`, `list_issues`, `search_issues`. They take explicit
  `owner` and `repo` arguments rather than inferring them.

Check with `command -v gh` before assuming the CLI is available.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a
  heredoc for multi-line bodies.
- **Read an issue**: several skills branch on labels, so a read that drops them
  is incomplete. Fetch them in the same call:
  ```bash
  gh issue view <number> --json number,title,body,labels,comments \
    --jq '{number, title, body, labels: [.labels[].name], comments: [.comments[].body]}'
  ```
  `gh issue view <number> --comments` is fine for eyeballing an issue by hand,
  but it returns no labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`
  with appropriate `--label` and `--state` filters.
- **Comment**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` /
  `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external
PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues, using
the `gh pr` equivalents — `gh pr view <n> --comments`, `gh pr diff <n>`,
`gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments`
filtered to `authorAssociation` of `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, or
`NONE`, then `gh pr comment` / `gh pr edit --add-label` / `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be
either — resolve with `gh pr view 42` and fall back to `gh issue view 42`.

Note that the autonomous loop opens no pull requests: ADR-0009 rescinded
PR-mode, and sessions merge to `main` directly. Any PR here is human-originated.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

The `gh issue view --json ... --jq ...` form above, or
`mcp__github__issue_read` in a cloud session.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as
tickets.

- **Map**: an issue labelled `wayfinder:map`, holding the Notes /
  Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (`gh api`
  on the sub-issues endpoint). Where sub-issues aren't enabled, add the child to
  a task list in the map body and put `Part of #<map>` at the top of the child
  body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`).
  Once claimed, assign the ticket to the driving dev.
- **Blocking**: GitHub's native issue dependencies. Add an edge with
  `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`,
  where `<blocker-db-id>` is the blocker's numeric **database id**
  (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _not_ the `#number` or
  `node_id`). Where dependencies aren't available, fall back to a
  `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is
  unblocked when every blocker is closed.
- **Frontier query**: list the map's open children, drop any with an open
  blocker or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me` — the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then
  `gh issue close <n>`, then append a context pointer to the map's
  Decisions-so-far.
