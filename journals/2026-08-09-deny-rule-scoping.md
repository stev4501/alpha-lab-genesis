# Session 2026-08-09 — supervised: deny rules scoped to the runner (BL-0006)

Not an autonomous session. The human operator directed this one end to end.
Recorded because it changes which layer refuses what, and the next agent to
read `docs/agents/domain.md` or ADR-0009 will otherwise be working from a
description of the enforcement stack that is no longer true.

## The decision

BL-0006 had been open since 2026-08-08 with three options and no answer. The
operator gave it in their own terms: the agent operating inside the GitHub
Action should avoid altering the core; a human working in the repository with
an agent should not be subject to that rule. That is option 3.

- **`loop/agent-settings.json`** (new, passed with `--settings`, binds the
  unattended agent only): `evaluator/`, `scripts/`, `schemas/`, `loop/`,
  `.github/`, `.claude/`, `CORE_MANIFEST.json`, `MISSION.md`, `CONTEXT.md`,
  `CODEOWNERS`, plus the `curl`/`wget`/`pip install`/`npm` denies.
- **`.claude/settings.json`** (binds every session in this repository):
  `results/`, `reviews/`, `data/snapshots|raw|provenance/`, and the
  `main`/history guardrails.

Nothing about ownership changed. ADR-0009's split — the agent owns operations,
the human owns the core — is untouched. What changed is that the human's
ownership of the core is now expressed to the agent that could actually violate
it unwatched, instead of to every session indiscriminately.

## What happened, in order

1. Read ADR-0009, BL-0006, `loop/run_session.sh`, `loop/validate_session.sh`,
   and the current deny rules. BL-0006 turned out to be exactly the operator's
   request, already written up with its options and its trade.
2. Asked which paths should stay repo-wide. The operator chose option 3.
3. Attempted the edit. **It was refused** — `.claude/settings.json` denied
   `Write` on `.claude/**` and `loop/**`, so the session could not apply the
   change to the rules that were blocking it.
4. Applied the three protected-path files through the GitHub API to this
   session's branch, at the operator's explicit direction, and pulled the
   result back down. BL-0006 records the same route being taken on 2026-08-08
   with the same authorization: "The API path was available the whole time;
   what made it legitimate was being asked for, not being reachable."
5. Wrote `tests/test_agent_settings.py` (10 tests), amended ADR-0009's
   "Enforcement, honestly, by layer", updated `docs/agents/domain.md`, and
   closed BL-0006.

## What surprised us

- **The API push dropped the executable bit** on `loop/run_session.sh`
  (100755 → 100644). Nothing in this repository would have caught it —
  `session.yml` invokes the runner as `bash loop/run_session.sh`, so it would
  have kept working — and it was noticed only because `git pull` printed the
  mode change. Restored with `git update-index --chmod=+x`. Worth remembering
  before the next protected-path change goes through the API.
- **The first version of the behavioural tests would have broken every
  autonomous run, and passed locally while doing it.** `run_session.sh` runs
  the selfcheck — `validate_repository.py` and the test suite — from inside its
  own `flock` region. A test that launches a runner on the default lock path
  therefore collides with the session running it: the child prints "another
  session is running", exits 0, and the assertion fails. Locally the lock is
  free, so the suite was green; under the loop it would have failed the
  selfcheck and put every session into maintenance mode. Caught in review on
  PR #15. `LOCKFILE` is now env-overridable, each scratch runner gets its own,
  and a regression test holds the default lock while running the preflight.
  Worth generalising: a test that shells out to `run_session.sh` is running
  inside the thing it is testing, and the environment it inherits is the loop's.
- **BL-0006's two-minute estimate for the patch handoff was low.** Step 3
  above is not the first recorded instance of a supervised session being unable
  to do the work it was convened to do — BL-0006's own observation section and
  its own commit history are two more. The friction was not the two minutes; it
  was that the only remaining route ran outside the tooling the rules describe.

## What the change deliberately does not do

- It does not weaken the unattended path. `loop/agent-settings.json` is a
  strict superset of `.claude/settings.json`, enforced by test, so a later
  trim of the repository default cannot loosen the session nobody is watching.
- It does not make the flag optional. The runner refuses to start when the
  settings file is missing or unparseable — tested by running the real
  preflight against a scratch repository, with a positive control so the test
  cannot pass by rejecting everything.
- It does not touch check 1 of `loop/validate_session.sh`. That check is still
  the layer that actually decides whether session output reaches `main`, and a
  new test derives its protected-path regex and asserts every path in it has a
  matching deny rule, so the two cannot drift apart silently.

## For the next session

Nothing here changes what an autonomous session may do — the deny rules it
runs under are identical, only their source file moved. If you are reading this
in a supervised session and find yourself able to edit `loop/` or `.claude/`
where you expected to be blocked: that is the change, and the convention still
stands. Propose core changes through `core_change_requests/` unless the
operator in the session asks for the edit directly.
