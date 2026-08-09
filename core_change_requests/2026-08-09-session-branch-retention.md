# CCR 2026-08-09: a retention policy for the branches the loop leaves behind

- Origin: supervised session, 2026-08-09, after the operator ran `session.yml`
  by `workflow_dispatch` and observed that the branch was still on the remote
  when the session ended
- Status: **proposed** — nothing applied. Patch attached and verified.
- Requires sealed changes: no
- Requires protected-path changes: yes (`loop/`, `.github/`) — human applies
- Related: `docs/adr/0008-mvp-reduction.md` (exit criterion 2),
  `docs/adr/0009-agent-owned-operations.md` ("The human owns the core"),
  `core_change_requests/2026-08-08-pr-mode-loop.md` ("Open questions for the
  human" → *Branch cleanup*)

## Why this exists

`core_change_requests/2026-08-08-pr-mode-loop.md` raised branch cleanup as an
open question for the human and left it there:

> **Branch cleanup.** The runner no longer deletes session branches. Nothing
> prunes `session/*`, `salvage/*`, `failed/*` over time.

ADR-0009 then withdrew that whole request, and the question went down with it
— not because it was answered, but because the document carrying it was
rescinded. It has been unowned since. This request picks up only that
question, rewritten against the runner that actually exists on `main` today
rather than the pull-request runner that briefly did.

No backlog item accompanies this. Every change proposed here is inside
`loop/` and `.github/`, so no session can act on it; a backlog entry would
only be an item the agent must skip.

## What the runner does today, precisely

Worth stating plainly, because the observation that prompted this — "the
branch it created does not get deleted" — is true of a narrower set of
branches than it appears. `loop/run_session.sh` can leave three kinds:

| Branch | Reaches the remote? | Deleted today? |
| --- | --- | --- |
| `session/<id>` (line 55) | **No.** On success it is merged locally and only `main` is pushed. | `git branch -D` at line 131 removes it from a clone that is discarded seconds later. |
| `failed/<id>` (line 141) | Yes, on validation failure. | Never. Deliberate — ADR-0008 exit criterion 2 requires the rejected work to be quarantined. |
| `unmerged/<id>` (line 134) | Yes, when the push to `main` is rejected after a passing validation. | Never. |

So the success path already leaves nothing behind, and the local `git branch
-D` is cosmetic on an ephemeral runner. What accumulates on the remote is
`failed/*` and `unmerged/*`, and only `failed/*` is a candidate for pruning.
The single branch on origin right now, `failed/2026-08-09-0505`, is the
0505 session that died 311 ms in on an unfunded `ANTHROPIC_API_KEY`; it is an
ancestor of `main` with an empty diff, and `HANDOFF.md` already records that
it holds no work and needs no salvage.

## What is proposed

Two new files, both attached as one patch
(`patches/2026-08-09-prune-session-branches.diff`, verified with `git apply
--check`):

- **`loop/prune_branches.sh`** — enumerates the remote with the refspec
  `refs/heads/failed/*` and nothing else, then applies two windows:
  `EMPTY_RETENTION_DAYS` (default 7) to branches holding no commits `main`
  lacks, `WORK_RETENTION_DAYS` (default 90) to branches that do.
- **`.github/workflows/prune-session-branches.yml`** — `workflow_dispatch`
  only, defaulting to a dry run, with the `schedule` block present but
  commented out. That mirrors `session.yml`'s own comment: a human enables the
  schedule after dispatch runs prove the loop end to end.

It is a separate workflow rather than a step in `run_session.sh` on purpose.
Cleanup belongs nowhere near the session's critical path — a `set -euo
pipefail` runner that fails while tidying up would fail a session that had
already succeeded — and its concurrency group is deliberately *not*
`research-session`, so a prune never queues behind a 110-minute session.

## Four things the work surfaced

### 1. `unmerged/*` must never be pruned, at any age

It is the one branch that exists *because* a validated session's work never
reached `main`. The runner's own comment at line 128 makes the point: the
clone is ephemeral, so an unpushed merge is an erased session. Deleting an
`unmerged/*` branch destroys the only copy of work that passed validation.
The script cannot reach one — it never enumerates a ref outside
`refs/heads/failed/*` — and that is a property of how the remote is listed,
not a rule applied afterwards.

### 2. Dating a failed branch by its tip commit is wrong, and dangerously so

A session that dies before producing a commit leaves `failed/<id>` pointing at
exactly the commit `main` pointed at when the session started. Its tip's
committer date is therefore `main`'s date, which can be arbitrarily old — a
branch created minutes ago can date to weeks ago. Any age rule reading the tip
would delete a fresh quarantine branch almost immediately, including one a
session had just pushed.

The fix is that `failed/<id>` carries `SESSION_ID` — `YYYY-MM-DD-HHMM`, set at
line 28 — in its own name, so age is parsed from the branch name. A name that
does not parse is kept, permanently, rather than guessed at. This also closes
the race with a running session without needing a lock: the shortest window is
7 days.

### 3. The salvage path can leave the branch as the only record

Line 141 pushes `failed/<id>` **before** the journal and handoff are committed
to `main`, and that ordering is right — preserve first, salvage second. But it
means a salvage push that is itself rejected (line 156, which exits 1) leaves
a `failed/` branch whose session has no journal on `main` at all. Pruning it
on age alone would erase the session entirely.

So a branch carrying unique commits is deleted only if
`journals/<id>.md` exists on `origin/main`. Absent journal, absent deletion,
regardless of age — the branch is kept for a human. Branches with no unique
commits skip this check, because there is nothing they could be the only copy
of.

### 4. Exit criterion 2 is about the salvage behaviour, not perpetual retention

ADR-0008 requires that one induced validation failure salvage correctly, with
rejected work quarantined to a `failed/` branch. A retention window does not
weaken that: the criterion is a statement about what happens at failure time.
But it does mean the demonstration should be evidenced in the journal and the
handoff, not by pointing at a branch that a later prune may collect. Worth
being explicit, since criterion 2 is still unattempted.

## Verification

`loop/prune_branches.sh` passes `bash -n`, and was exercised against a
synthetic remote carrying one branch of each shape. Every decision path fired,
and `main` and `unmerged/*` were untouched by both the dry and the live run:

```
DELETE failed/2020-01-01-0101 — no unique commits, 2412d old, past 7d
DELETE failed/2020-02-02-0202 — 1 unique commit(s), 2380d old, past 90d
KEEP   failed/2020-03-03-0303 — 1 unique commit(s), 2350d old, but journals/2020-03-03-0303.md is absent from main
KEEP   failed/hand-made — name carries no parseable session id
Deleted 2 branch(es), kept 2.
```

Run unmodified against this repository's real remote in dry-run mode, it
reports:

```
KEEP   failed/2026-08-09-0505 — no unique commits, 0d old, retained 7d
Dry run: 0 branch(es) would be deleted, 1 kept.
```

which is the intended behaviour: that branch becomes eligible on 2026-08-16,
and until then the pruner declines to touch a branch a session may still be
writing to.

Nothing here is covered by `tests/`, and nothing here is imported by anything
under test, so the suite is unaffected — which matters, because a red suite
flips the next session into maintenance mode.

## For the human to decide

1. **The windows.** 7 days for empty, 90 for work-carrying, are proposals, not
   findings. They are environment variables in the workflow; changing them is
   a one-line edit and needs no code change.
2. **Whether to enable the schedule.** Shipping it commented out follows
   `session.yml`'s precedent. At the current rate — two dispatches, one
   failure — the manual path is honestly sufficient, and the schedule can wait
   until sessions run unattended.
3. **Where the policy is recorded.** This document records the reasoning, but
   a retention rule is a governance statement about evidence, and ADR-0008's
   exit criterion 2 is the text a future reader will land on. A one-paragraph
   amendment there, or an ADR-0010, would put it where it is looked for.
4. **`failed/2026-08-09-0505` specifically.** It is independent of all of the
   above. It holds nothing, `HANDOFF.md` says so, and deleting it by hand today
   costs nothing and waits on no approval.

## How to apply

```
git apply core_change_requests/patches/2026-08-09-prune-session-branches.diff
chmod +x loop/prune_branches.sh    # the patch sets mode 100755; belt and braces
```

Then run the workflow once by dispatch with `dry_run` left at its default and
read the output before considering the schedule. The workflow needs no
credential beyond the default `GITHUB_TOKEN` with `contents: write`, which
ADR-0009 already settled as the loop's ceiling — this adds no new secret,
no machine account, and no permission the loop does not already hold.

## What this does not change

`loop/run_session.sh`, `loop/validate_session.sh`, `session.yml`, every sealed
component, `CORE_MANIFEST.json`, and the deny rules are all untouched. The
patch adds two files and edits none. Reverting is `git rm` on both.
