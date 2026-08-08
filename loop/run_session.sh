#!/usr/bin/env bash
# run_session.sh — one autonomous session for alpha-lab-genesis, start to finish.
# Lives in loop/ (protected). The session agent never edits this file.
#
# Flow: preflight -> selfcheck -> branch -> claude -p -> validate -> merge | salvage
# Invariant: main is always consistent; a failed session leaves only its
# journal + handoff on main and its full branch under failed/ for forensics.

set -euo pipefail

# ---------- config (env-overridable) ----------
REPO_DIR="${REPO_DIR:-$(git rev-parse --show-toplevel)}"
SESSION_MINUTES="${SESSION_MINUTES:-90}"        # hard wall clock for the agent
MAX_TURNS="${MAX_TURNS:-80}"
MAX_BUDGET_USD="${MAX_BUDGET_USD:-5}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
LOCKFILE="/tmp/alpha-lab-session.lock"

cd "$REPO_DIR"

# ---------- no overlapping sessions ----------
exec 9>"$LOCKFILE"
if ! flock -n 9; then
  echo "Another session is running; exiting." >&2
  exit 0
fi

SESSION_ID="$(date -u +%Y-%m-%d)-$(date -u +%H%M)"
BRANCH="session/${SESSION_ID}"
LOGDIR="logs/loop/${SESSION_ID}"
mkdir -p "$LOGDIR"

log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOGDIR/runner.log"; }

# ---------- preflight: repo must be clean, on main, current ----------
git checkout -q main
if [[ -n "$(git status --porcelain)" ]]; then
  log "FATAL: dirty working tree on main. A previous run died badly. Manual fix required."
  exit 1
fi
git pull --ff-only -q origin main || log "WARN: pull failed (offline?); continuing on local main."

# ---------- selfcheck decides research vs maintenance ----------
MODE="research"
if ! { python scripts/validate_repository.py && python -m pytest tests -q; } \
     > "$LOGDIR/selfcheck.log" 2>&1; then
  MODE="maintenance"
  log "Selfcheck FAILED -> maintenance mode. See $LOGDIR/selfcheck.log"
fi

PROMPT_FILE="loop/prompts/session.md"
[[ "$MODE" == "maintenance" ]] && PROMPT_FILE="loop/prompts/maintenance.md"

# ---------- session branch ----------
git checkout -q -b "$BRANCH"

# ---------- build prompt (inject session facts; agent self-manages to soft deadline) ----------
SOFT_DEADLINE_UTC="$(date -u -d "+$(( SESSION_MINUTES * 80 / 100 )) minutes" +%H:%M 2>/dev/null \
                  || date -u -v "+$(( SESSION_MINUTES * 80 / 100 ))M" +%H:%M)"
PROMPT="$(sed -e "s/{{SESSION_ID}}/${SESSION_ID}/g" \
              -e "s/{{SOFT_DEADLINE_UTC}}/${SOFT_DEADLINE_UTC}/g" \
              -e "s/{{MODE}}/${MODE}/g" "$PROMPT_FILE")"

# ---------- run the agent, hard-capped ----------
# allowedTools is scoped to this repository's real scripts. NOTE the space
# before * in Bash patterns — "Bash(git add *)" matches "git add <anything>",
# while "Bash(git add*)" would also match "git addx". PermissionRequest hooks
# do NOT fire in -p mode; .claude/settings.json deny rules and this allowlist
# are the only permission layers before validation.
#
# Deliberately NOT allowlisted: "cat" and "ls". Bash patterns match the command
# string, so "cat x > loop/validate_session.sh" satisfies "Bash(cat *)" while
# writing to a path the Edit/Write deny rules protect. Read, Glob, and Grep
# already cover every legitimate use, so the redirection class is removed
# rather than pattern-matched around.
set +e
timeout --signal=TERM "${SESSION_MINUTES}m" \
  "$CLAUDE_BIN" -p "$PROMPT" \
    --allowedTools "Read,Glob,Grep,Edit,Write,Bash(git status),Bash(git status *),Bash(git add *),Bash(git commit *),Bash(git log *),Bash(git diff *),Bash(git show *),Bash(python scripts/validate_repository.py *),Bash(python scripts/validate_repository.py),Bash(python scripts/preregister_experiment.py *),Bash(python scripts/finalize_experiment.py *),Bash(python scripts/record_evidence_review.py *),Bash(python scripts/register_market_snapshot.py *),Bash(python scripts/normalize_finance_ohlcv.py *),Bash(python evaluator/daily_bar.py *),Bash(python -m pytest *),Bash(mkdir -p *)" \
    --max-turns "$MAX_TURNS" \
    --max-budget-usd "$MAX_BUDGET_USD" \
    --output-format json \
    > "$LOGDIR/agent_result.json" 2> "$LOGDIR/agent_stderr.log"
AGENT_EXIT=$?
set -e
log "Agent exited: $AGENT_EXIT (timeout=124, turn/budget limits also nonzero)"

# Commit anything the agent left uncommitted so validation sees the full session.
git add -A
git commit -q -m "session ${SESSION_ID}: auto-commit residual changes" || true

# ---------- validate ----------
# Run the validator from main, never from the branch under test: a session that
# tampered with loop/validate_session.sh must not be handed the job of judging
# itself. set -e aborts the run if main's copy cannot be read — fail closed.
TRUSTED_VALIDATOR="$(mktemp)"
trap 'rm -f "$TRUSTED_VALIDATOR"' EXIT
git show "main:loop/validate_session.sh" > "$TRUSTED_VALIDATOR"
chmod +x "$TRUSTED_VALIDATOR"
if "$TRUSTED_VALIDATOR" main "$BRANCH" "$SESSION_ID" > "$LOGDIR/validate.log" 2>&1; then
  log "Validation PASSED -> merging to main."
  git checkout -q main
  git merge -q --no-ff -m "session ${SESSION_ID} (${MODE}, agent_exit=${AGENT_EXIT})" "$BRANCH"
  # Never delete the session branch before its work is durably on the remote.
  # This runner's clone is ephemeral, so an unpushed merge is an erased session,
  # and there is nothing for a later run to "retry" from.
  if git push -q origin main; then
    git branch -q -D "$BRANCH"
  else
    log "FATAL: push to main rejected — preserving session work at unmerged/${SESSION_ID}."
    git push -q origin "$BRANCH:unmerged/${SESSION_ID}" \
      || log "FATAL: could not preserve remotely; work exists only on this runner."
    exit 1
  fi
else
  log "Validation FAILED -> salvage. See $LOGDIR/validate.log"
  # Preserve the failed branch for forensics.
  git push -q origin "$BRANCH:failed/${SESSION_ID}" || true
  git checkout -q main
  # Salvage ONLY narrative artifacts; discard everything else.
  git checkout "$BRANCH" -- "journals/" "HANDOFF.md" 2>/dev/null || true
  {
    echo ""
    echo "## SESSION ${SESSION_ID} FAILED VALIDATION"
    echo "Branch preserved at failed/${SESSION_ID}. First failed check:"
    grep -m1 "^FAIL" "$LOGDIR/validate.log" || echo "(see ${LOGDIR}/validate.log)"
    echo "Next session: treat this as maintenance input."
  } >> HANDOFF.md
  git add -A
  git commit -q -m "session ${SESSION_ID}: FAILED validation — journal/handoff salvaged"
  # The session branch is already preserved at failed/${SESSION_ID} above, so a
  # rejected salvage push loses nothing — but it must still be loud, not a WARN.
  if git push -q origin main; then
    git branch -q -D "$BRANCH"
  else
    log "FATAL: salvage push to main rejected; session branch retained locally."
    exit 1
  fi
fi

log "Session ${SESSION_ID} complete."
