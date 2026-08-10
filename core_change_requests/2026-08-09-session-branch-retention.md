# CCR 2026-08-09: a retention policy for the branches the loop leaves behind

- Origin: supervised session, 2026-08-09, after the operator ran `session.yml`
  by `workflow_dispatch` and observed that the branch was still on the remote
  when the session ended
- Status: **APPLIED 2026-08-10** in a supervised session, at the operator's
  direction, **plus one round-4 fix** — a code review of the applied change
  found that the retention windows fail *open* on a malformed value, which
  inverts the policy this request exists to set. The attached patch has been
  regenerated to include the fix, so document and code still agree; it is no
  longer the byte-for-byte artifact reviewed in rounds 1-3. See "Review round
  4" and "Decided 2026-08-10" below.
  Revised 2026-08-09 after review rounds 1-3 on PR #13; see those sections.
- Requires sealed changes: no
- Requires protected-path changes: yes (`loop/`, `.github/`) — human applies
- Related: `docs/adr/0008-mvp-reduction.md` (exit criterion 2),
  `docs/adr/0009-agent-owned-operations.md` ("The human owns the core"),
  `README.md` ("Source-of-Truth Rules"),
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
  lacks, and `WORK_RETENTION_DAYS` to branches that do. **That second window
  defaults to 0, meaning never** — out of the box this deletes only branches
  that hold nothing. See review finding 1 below for why.
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
Under the shipped default the question is moot — the criterion-2 branch will
carry work, and work-bearing branches are never deleted. It matters only if
`WORK_RETENTION_DAYS` is ever raised, and then the demonstration should be
evidenced in the journal and the handoff rather than by pointing at a branch a
later prune may collect. Worth stating, since criterion 2 is still unattempted.

## Review round 1 (PR #13, 2026-08-09)

Five findings. Three were real defects in the first draft, one changed the
default posture, and one was a style point taken as offered. All are fixed in
the attached patch.

### 1. Deleting work-bearing branches contradicts a source-of-truth rule

`README.md:65` states, under *Source-of-Truth Rules*: "Failed and discarded
experiments are retained." A `failed/<id>` branch carrying commits is the only
copy of the artifacts that session produced — its journal on `main` records
what happened, not what was made. A 90-day default therefore proposed erasing
retained evidence on a timer, which is not this request's job to decide.

`WORK_RETENTION_DAYS` now defaults to **0, meaning never**. The default
posture deletes only branches holding no commits `main` lacks, which is both
the observed problem and the case where nothing can be lost. The window
remains implemented and tested, so raising it is a one-line change once the
README rule is amended — but that amendment is a human decision, and the
default no longer presumes it.

### 2. Deletion read stale state and deleted by name (real, and the dangerous one)

The first draft fetched, then ignored the SHA `git ls-remote` returned,
evaluated the tracking ref, and deleted by branch name with no lease. A branch
that gained work between fetch and delete would have been deleted on the
strength of a judgement made about a different commit — including its journal
check.

The enumerated SHA is now the authority for the whole run, and deletion goes
through `--force-with-lease=refs/heads/<branch>:<sha>`. If the branch moved,
the remote refuses and the work survives to be re-evaluated next run.

### 3. A branch with no local tracking ref aborted the entire job

Under `set -euo pipefail`, `git rev-list --count origin/main..origin/failed/X`
on a branch absent from the local clone exits 128 and takes the job down —
verified, not inferred. Any branch created between the fetch and the
enumeration triggered it, and one unlucky branch stopped every other branch
from being evaluated. The script now checks the enumerated commit is in hand
with `git cat-file -e` and keeps the branch if it is not.

### 4. Uncommenting the schedule silently disabled the manual trigger

Worse than a duplicate key. The commented block sat at column 0, so
uncommenting it produced a second top-level `on:` — and YAML keeps the last
one. Parsing the uncommented file yields `{'schedule': ...}` alone: the
`workflow_dispatch` trigger, and with it the `dry_run` input, silently
vanishes, leaving a scheduled pruner that deletes for real with no manual
trigger and no way to dry-run it. The commented `schedule:` is now nested
under the existing `on:` mapping, with a comment saying why it must stay
there.

### 5. Duplicated keep paths

Three paths repeated log/increment/continue. Folded into a `keep()` helper;
the four keep paths that now exist each read as one line.

## Review round 2 (PR #13, 2026-08-09)

One finding, and a real one: **every push failure was reported as a stale
lease.** The deletion path sent `git push` diagnostics to `/dev/null` and
treated any nonzero exit as the benign race, so an expired token, a revoked
permission, branch protection, or a 500 from the remote all printed
`branch moved since enumeration` and the job exited 0.

That is the worst failure mode this script could have. A pruner that reports a
clean run while silently deleting nothing is worse than one that crashes,
because a crash gets looked at and a clean run does not — and the operator's
conclusion ("pruning works") would be wrong for as long as the credential
stayed broken.

A stale lease is now the only nonzero exit treated as benign, matched against
the preserved stderr rather than assumed from the exit code. Every other
failure prints git's own diagnostics and increments a counter that makes the
workflow exit 1. `LC_ALL=C` pins the message the match depends on, so a
localized runner cannot turn a real error back into a silent keep.

The three deletion outcomes are now distinguishable, which they were not
before: deleted, benignly skipped, and broken.

## Review round 3 (PR #13, 2026-08-09)

Two findings, both accepted, plus one judgment call declined with reasons.

### Enumeration failures reported a clean run

`mapfile -t REMOTE_REFS < <(git ls-remote ...)` reports *mapfile's* status, not
the producer's. A failed enumeration — no network, dead credential — left an
empty array, and the run printed `0 deleted, 0 kept` and exited 0. Confirmed
directly: producer `false`, `mapfile status=0`, zero entries, script survives.

This is the same shape as the round 2 defect: a failure that presents as an
uneventful success. The listing is now captured through a command
substitution whose status is checked, and a failed enumeration is fatal. An
enumeration that did not happen must not look like a remote with nothing on
it; a listing that genuinely returns nothing still exits 0.

### Stale-lease detection was text-fragile

`grep -qF "stale info"` treated any stderr containing that phrase as a benign
race, and a hook is free to print anything in its rejection — including that.
Git's wording is not an interface, and `LC_ALL=C` only ever constrained our own
side of it.

Detection is now made from remote state rather than text. After a failed push
the remote is re-queried for that ref: unchanged means the push failed on its
own account and is an error; moved or absent is the race the lease exists to
catch; and a re-query that itself fails leaves the outcome unknown, which is an
error rather than a keep. `LC_ALL=C` stays, but only so diagnostics land in the
log predictably — nothing branches on what it says.

Verified with a hook that rejects the deletion *and prints the phrase
`stale info` in its message*. The old code would have called that a benign
race; it is now correctly an error, because the ref is still sitting on the
commit that was judged.

### Declined: removing the dormant `WORK_RETENTION_DAYS` path

The reviewer flagged, as a judgment call, that shipping a positive-value code
path invites a future configuration-only policy violation. The path is kept,
for a reason specific to this repository: `WORK_RETENTION_DAYS` is set in
`.github/workflows/prune-session-branches.yml`, and `.github/` is protected.
Changing it from 0 is not a configuration tweak — it is a human editing a
protected file, which is the same gate the `README.md` amendment itself would
pass through. The activation risk the finding describes is already held by the
layer ADR-0009 relies on everywhere else.

Removing the path would also delete the thing the human is being asked to
decide in this request, leaving no implementation behind the question.

What was missing is that the conflict was documented only in comments. The
script now prints a warning naming `README.md` whenever the value is positive,
so an armed policy change is visible in the run log rather than only to
someone reading the source at 04:17 on a Sunday.

## Verification

`loop/prune_branches.sh` passes `bash -n`. It was exercised against a
synthetic remote carrying one branch of each shape, with the two race
conditions injected by a `git` shim rather than argued about. `main` and
`unmerged/*` were untouched in every run.

Default posture — only the empty branch is eligible:

```
WOULD  failed/2020-01-01-0101 — no unique commits, 2412d old, past 7d
KEEP   failed/2020-02-02-0202 — 1 unique commit(s); WORK_RETENTION_DAYS=0 retains rejected work indefinitely
KEEP   failed/2020-03-03-0303 — 1 unique commit(s); WORK_RETENTION_DAYS=0 retains rejected work indefinitely
KEEP   failed/hand-made — name carries no parseable session id
Dry run: 1 branch(es) would be deleted, 3 kept.
```

Opt-in (`WORK_RETENTION_DAYS=90`) — the journal guard still binds:

```
WOULD  failed/2020-02-02-0202 — 1 unique commit(s), 2380d old, past 90d
KEEP   failed/2020-03-03-0303 — 1 unique commit(s), 2350d old, but journals/2020-03-03-0303.md is absent from main
```

Enumerated commit absent locally (finding 3; previously exit 128 for the whole
job) — now a keep, exit 0:

```
KEEP   failed/2020-02-02-0202 — commit 639fee80 not present locally; state moved under us
```

Branch gains work between enumeration and delete, injected live during a
`DRY_RUN=false` run (round 1 finding 2) — the lease refuses and the work
survives, and this stays a keep with exit 0 after the round 2 change:

```
KEEP   failed/2020-01-01-0101 — moved since enumeration (02b098cd -> 9e52e3e2); lease refused
Deleted 0 branch(es), kept 1.
script exit=0
```

Remote refuses the deletion for a reason that is not a lease mismatch (rounds 2
and 3), reproduced with a `pre-receive` hook standing in for branch protection.
The hook deliberately prints `stale info` in its rejection, which the round 2
text match would have swallowed; the ref is unchanged, so it is an error:

```
ERROR  failed/2020-01-01-0101 — deletion failed and the branch still points at 02b098cd,
       so this was not a lease race:
       remote: rejected: stale info is not the reason, this is branch protection
        ! [remote rejected] failed/2020-01-01-0101 (pre-receive hook declined)
Deleted 0 branch(es), kept 0.
FATAL: 1 deletion(s) failed for reasons other than a stale lease.
script exit=1
```

Enumeration itself fails (round 3) — previously `0 deleted, 0 kept` and exit 0:

```
FATAL: could not enumerate refs/heads/failed/* on origin; nothing was evaluated.
exit=1
```

Another actor deletes the branch first — benign, since the outcome is the one
intended:

```
KEEP   failed/2020-01-01-0101 — already gone from the remote; another actor deleted it
script exit=0
```

Ordinary successful deletion, confirming the stricter handling did not break
the path it guards:

```
DELETE failed/2020-01-01-0101 — no unique commits, 2412d old, past 0d
Deleted 1 branch(es), kept 0.
script exit=0
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

1. **Whether rejected work is ever deleted at all.** This is the live one.
   `README.md:65` retains failed and discarded experiments, so
   `WORK_RETENTION_DAYS` ships at 0 and work-bearing `failed/*` branches are
   kept forever. Raising it needs that rule amended first — or the branch
   contents archived somewhere durable before deletion, which is a larger
   change than this request and is not proposed here. Leaving it at 0 is a
   complete answer; the loop's actual clutter is the empty branches.
2. **The empty window.** 7 days is a proposal, not a finding. It is an
   environment variable in the workflow; changing it is a one-line edit.
3. **Whether to enable the schedule.** Shipping it commented out follows
   `session.yml`'s precedent. At the current rate — two dispatches, one
   failure — the manual path is honestly sufficient, and the schedule can wait
   until sessions run unattended.
4. **Where the policy is recorded.** This document records the reasoning, but
   a retention rule is a governance statement about evidence, and ADR-0008's
   exit criterion 2 is the text a future reader will land on. A one-paragraph
   amendment there, or an ADR-0010, would put it where it is looked for.
5. **`failed/2026-08-09-0505` specifically.** It is independent of all of the
   above. It holds nothing, `HANDOFF.md` says so, and deleting it by hand today
   costs nothing and waits on no approval.

## Review round 4 (2026-08-10, after applying)

One finding, and it is the same shape as rounds 2 and 3: a failure that
presents as an uneventful success. Those two hardened the *output* paths — the
push, the re-query, the enumeration. Nobody had looked at the *input* path.

`EMPTY_RETENTION_DAYS` and `WORK_RETENTION_DAYS` arrive from workflow env and
are used only in `[[ ]]` arithmetic. That context fails **open** on a value it
cannot parse: `[[ "7d" -gt 0 ]]` does not abort under `set -e` — it prints an
error and evaluates false. With `WORK_RETENTION_DAYS="7d"`, all three guards
that depend on it evaluate false at once:

- the policy warning stays silent;
- the `[[ "$limit" -le 0 ]]` retain-forever guard is skipped;
- the `[[ "$age_days" -lt "$limit" ]]` age guard is skipped.

So the branch reaches the delete path **at any age**, and the run exits 0.
Demonstrated against the synthetic remote — the work-bearing branch flips from

```
KEEP   failed/2020-02-02-0202 — 1 unique commit(s); WORK_RETENTION_DAYS=0 retains rejected work indefinitely
```

to

```
WOULD  failed/2020-02-02-0202 — 1 unique commit(s), 2381d old, past 7dd
```

A typo in a protected workflow file silently inverts "never delete rejected
work" into "delete it at any age" — the exact opposite of what this request
sets out to guarantee, and a direct breach of `README.md`'s "Failed and
discarded experiments are retained". The `past 7dd` in that line is the only
tell, and it appears in a log nobody reads on a green run.

Two things bound the blast radius but neither closes it: the journal guard
still keeps a branch whose journal never reached `main`, and the shipped
default of `0` is well-formed. The hole opens precisely when a human edits
`WORK_RETENTION_DAYS` — which is the moment this request is designed for.

**Fix:** validate both windows before anything is judged, and fail closed.
Leading zeros are rejected rather than tolerated, because `[[ ]]` reads them as
octal and that fails in both directions: `08` and `09` are invalid octal and
fail open exactly like `7d`, while `010` parses fine and silently means 8. A
window that quietly means something other than what the workflow says is worse
than one that refuses to start.

Verified: `7d`, `abc`, `-1`, `08`, `09`, `007`, `010`, `" 7"`, `"7 "`, `1e3`,
and a command-substitution payload all exit 1 before any branch is evaluated;
`0`, `7`, `90`, `365` all run normally. `[[ ]]` evaluates array subscripts, so
the injection case is not hypothetical.

The attached patch was regenerated to include this, and reproduces the applied
tree byte-for-byte at mode 755 from a clean `origin/main` worktree.

### Two things left as findings rather than fixed

- **The journal-name contract is divergent.** This script requires
  `journals/<id>.md` exactly; `loop/validate_session.sh:167` accepts any added
  file whose name merely *contains* the session id, and `journals/` already
  holds both shapes (`2026-08-09-0525.md` and
  `2026-08-09-deny-rule-scoping.md`). A journal named `<id>-topic.md` passes
  validation but is invisible to the pruner's guard. It fails safe — the
  branch is kept — but two files now state one rule differently. Reconciling
  them means editing `validate_session.sh`, which is its own request.
- **`removed` counts branches that were not removed** on the dry-run path.
  Cosmetic; left alone to keep the divergence from the reviewed artifact as
  small as the defect required.

## Decided 2026-08-10 (supervised session)

The operator directed that this request be applied. Questions 1-3 were taken
at the shipped defaults, which is the posture the patch already encoded.
Questions 4 and 5 have no shipped default — 4 was deferred and 5 was decided
against the request's own recommendation, so both are recorded as decisions
taken rather than defaults accepted:

1. **Rejected work is never deleted.** `WORK_RETENTION_DAYS` stays 0.
   `README.md`'s source-of-truth rule is not amended, and nothing in this
   change asks it to be. The positive-value path ships dormant and warns in
   the run log if it is ever armed — and, after round 4, refuses to start at
   all on a value that would have armed it by accident.
2. **Empty window: 7 days**, as proposed.
3. **Schedule stays commented out.** Manual dispatch only, following
   `session.yml`'s precedent.
4. **Deferred, not answered.** The policy is recorded here, in this document.
   The ADR-0008 amendment or ADR-0010 the request suggests was *not* written.
   This is the one question the request asked that this session did not close
   — see the note below.
5. **Decided against the request's recommendation.**
   `failed/2026-08-09-0505` was *not* hand-deleted. The request says it
   "costs nothing and waits on no approval", and its facts hold — the branch
   is confirmed empty (`git rev-list --count origin/main..d162587` is 0). It
   was retained anyway: it is one day old and therefore inside the 7-day
   window, and letting the mechanism this request adds collect it on its
   first real run is a better proof of the rule than a manual deletion that
   bypasses it. Recorded plainly because it reverses a recommendation rather
   than accepting a default, and a later reader should not mistake it for
   the latter.

Still open after this: decision 4's *placement*. The retention rule now
exists in code and in this document, but a reader arriving at ADR-0008's exit
criterion 2 will not find it. That is a one-paragraph amendment and a
governance call the operator has not yet made.

### Independent verification before applying

The synthetic-remote exercise described under "Verification" was reproduced
from scratch in the applying session rather than taken on trust — one branch
of each shape against a real bare remote, with the races injected through a
`git` shim and a `pre-receive` hook:

- default posture deletes only the empty branch; `main` and `unmerged/*`
  untouched;
- `WORK_RETENTION_DAYS=90` arms the work-bearing path, and the journal guard
  still keeps the branch whose journal is absent from `main`;
- work landing between enumeration and deletion loses the lease, survives,
  and the run exits 0;
- a failed enumeration is fatal rather than a tidy `0 deleted, 0 kept`;
- a `pre-receive` hook that rejects the deletion **while printing the phrase
  `stale info`** is correctly reported as an error and exits 1 — the round-3
  finding, confirmed against the behaviour that would have laundered it.

`python scripts/validate_repository.py` is valid and the test suite is 78
tests, OK. Note that it was run here with `python -m unittest discover -s
tests`, not `pytest`: `loop/validate_session.sh:151` invokes
`python -m pytest tests -q`, and `pytest` is not installed in the Alpha Lab
Dev cloud environment. Same test files, different runner — but the runner the
loop actually uses was not the one exercised here.

What this exercise did **not** cover, and should have: any malformed value for
the two retention windows. Every case above varies the *remote*; none varies
the *input*. That gap is exactly where round 4's finding was hiding, and it is
worth stating as a lesson about the shape of this verification rather than
quietly fixing — a test matrix that only perturbs one side of a program will
keep finding defects on that side only.

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
