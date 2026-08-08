# Session 2026-08-08 — human-supervised MVP reduction

Not an autonomous session. A human supervised this session end to end and
approved each irreversible step; it executed ADR-0008. Recorded here so the
first autonomous session inherits an accurate account of how the current
tree came to be.

## What was done

1. Baseline captured: `scripts/validate_repository.py` valid,
   `python -m pytest tests -q` 23 passed / 17 subtests. SHA-256 of all 19
   files under `results/` recorded outside the repo and re-verified
   unchanged at the end.
2. Annotated tag `pre-mvp-freeze` created on the pre-reduction `main`
   commit and pushed by the human (the session's credentials could not push
   tags). It is the source of truth for all parked components.
3. ADR-0008 written and linked from `DECISIONS.md`.
4. Parked four docs (`capability-map`, `scheduled-task-specification`,
   `source-evaluation`, `tooling-recommendations`) via `git rm`.
5. Skill parking was BLOCKED: sealed `scripts/validate_repository.py`
   hardcodes all nine skills. Human directed the six intended-park skills to
   remain in place, dormant, pending the G-0004 change (see BL-0002).
6. Deleted `data/SPY_*.csv` duplicates after verifying byte-identity with
   the `data/snapshots/` content-addressed copies and confirming
   `DATA_MANIFEST.json` resolves only snapshot paths.
7. Added loop machinery: `loop/run_session.sh`, `loop/validate_session.sh`
   (fail-closed; sealed hashes verified against the `pre-mvp-freeze` tag),
   prompts, manual-only workflow, `.claude/settings.json` deny rules,
   `CODEOWNERS`.
8. Seeded `HANDOFF.md` and `backlog/` BL-0001..BL-0004.

## What surprised us

- The sealed validator's hardcoded skill list turned an intended one-commit
  parking into a G-0004 dependency. The reduction plan said to stop rather
  than work around it; we stopped, and the human amended the scope.

## For the next session

Orient from `HANDOFF.md`. The only sanctioned work is `backlog/`. Branch
protection on `main` and the workflow schedule are still pending human
action in GitHub settings.
