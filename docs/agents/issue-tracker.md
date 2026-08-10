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

### REST fallback in cloud sessions, narrowly scoped

The MCP tool set does not cover every operation these skills need. Where it
does not, and only there, call the GitHub REST API directly with `curl`,
authenticating with the `GH_TOKEN` already present in the session environment;
it reaches `api.github.com` through the agent proxy. Conditions, all of them:

- **MCP wins wherever it reaches.** Use REST only when no `mcp__github__*`
  tool covers the operation — verify by looking, not by assuming. Convenience
  is not a reason; an MCP tool that is merely more awkward still wins.
- **Read back through MCP.** Where an MCP read exists for what you wrote,
  confirm the result with it, so the write is verified by something other than
  the tool that performed it.
- **Never print the token**, in command output, logs, commit messages, or
  issue comments. Redact API responses before echoing them.
- **Record the gap here** when you hit a new one, so the list below stays the
  authoritative account of where MCP falls short.

Known gaps:

| Operation | Why REST | MCP equivalent |
| :--- | :--- | :--- |
| Create or update a label | `/triage` applies labels, which fails if the label does not exist | `get_label` reads; there is no create or update tool |
| Add an issue dependency (`blocked_by`) | `/wayfinder` records blocking edges between tickets | `sub_issue_write` covers parent/child hierarchy only, which is a different relation; there is no dependency tool, and no MCP read either |

The label recipe itself lives in `triage-labels.md`, next to the label
definitions it depends on.

Issue dependencies are the one gap where the read-back condition cannot be
satisfied as written, because MCP has no dependency read either. Verify with a
REST `GET` on the same endpoint instead, and say so wherever the write is
reported.

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
  `node_id`). In a cloud session this is the REST fallback above, not a reason
  to skip the edge:

  ```bash
  curl -sS -X POST -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by" \
    -d '{"issue_id":<blocker-db-id>}'
  ```

  Fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body
  only where dependencies are genuinely unavailable — meaning the API rejects
  the call for this repository, not merely that `gh` is missing from the
  session. Confirm which by reading the endpoint before assuming; on
  `stev4501/alpha-lab-genesis` it answers. A ticket is unblocked when every
  blocker is closed.
- **Frontier query**: list the map's open children, drop any with an open
  blocker or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me` — the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then
  `gh issue close <n>`, then append a context pointer to the map's
  Decisions-so-far.
