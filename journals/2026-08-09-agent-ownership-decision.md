# Session 2026-08-09 — supervised: agent ownership decided (ADR-0009)

Not an autonomous session. A human directed this session end to end. Recorded
so the first autonomous session inherits an accurate account of why the loop
it wakes into is direct-push and not pull-request-based.

## What happened, in order

1. BL-0005's steps 1 and 2 were drafted as patches (PR #4) and the human
   applied them to `main` (PR #5, `8906f4f`): pull-request-mode runner,
   `session-validate.yml`, `SESSION_PR_TOKEN` wiring.
2. An adversarial review of the credential options for that design found that
   every workable variant either handed the session a repository-write
   credential anyway or put a human approval inside every session.
3. Reviewing yoyo-evolve — this experiment's inspiration, which pushes `main`
   directly under a GitHub App and gates itself only with its own test
   suite — surfaced the real question: is the agent meant to own the repo?
4. The human answered directly: yes for operations, no for the core. The
   agent owns forward motion; the human owns sealed components, loop
   machinery, generation changes, and approvals (the G-0004 round trip
   stands).
5. ADR-0009 records the decision. BL-0005 is rescinded, its change request
   withdrawn, and a verified revert patch
   (`core_change_requests/patches/2026-08-09-rescind-pr-mode.diff`, equal to
   `git revert 8906f4f`) awaits the human's hands, since `loop/` and
   `.github/` remain human-applied paths.

## What surprised us

- The applied BL-0005 machinery was live on `main` for under a day before
  being rescinded — not because it was broken (it was verified working) but
  because it solved a problem the actual intent defines out of existence.
  The five findings in the withdrawn change request stay true; keep them.
- Under agent ownership the credential question dissolves entirely: the
  default `GITHUB_TOKEN` suffices, and the best token design is no token.

## For the next session

Orient from `HANDOFF.md`. Exit criterion 1 counting starts with the first
scheduled session after the human applies the revert. The sanctioned work is
unchanged: `backlog/`, highest-priority open item first (BL-0001).
