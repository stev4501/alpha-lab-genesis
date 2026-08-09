#!/usr/bin/env bash
# run_session.sh — one autonomous session for alpha-lab-genesis, start to finish.
# Lives in loop/ (protected). The session agent never edits this file.
#
# Flow: preflight -> selfcheck -> branch -> claude -p -> validate -> pull request
# Invariant: this runner never writes main. Every path out of a session ends at
# an open pull request, so the merge decision belongs to the required check and
# a CODEOWNERS review rather than to the session itself (BL-0005). A failed
# session still gets its journal + handoff to main, but through a salvage pull
# request; its full branch is preserved under failed/ for forensics.

set -euo pipefail

# ---------- config (env-overridable) ----------
REPO_DIR="${REPO_DIR:-$(git rev-parse --show-toplevel)}"
SESSION_MINUTES="${SESSION_MINUTES:-90}"        # hard wall clock for the agent
MAX_TURNS="${MAX_TURNS:-80}"
MAX_BUDGET_USD="${MAX_BUDGET_USD:-5}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
LOCKFILE="/tmp/alpha-lab-session.lock"

# gh authenticates from GH_TOKEN. The workflow supplies it; see the note in
# .github/workflows/session.yml about which token, and why it is not always
# the default GITHUB_TOKEN.

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

# ---------- pull request helper ----------
# The runner's job ends at "pull request opened". Merging is the gate's job:
# the required check from .github/workflows/session-validate.yml plus a
# CODEOWNERS review. Nothing below this line may push main.
open_pull_request() {
  local branch="$1" title="$2" body="$3"
  if ! command -v gh >/dev/null 2>&1; then
    log "FATAL: gh not found; ${branch} is pushed but no pull request was opened."
    return 1
  fi
  if ! gh pr create --base main --head "$branch" --title "$title" --body "$body" \
       >>"$LOGDIR/runner.log" 2>&1; then
    log "FATAL: gh pr create failed for ${branch}; the branch is pushed, open it by hand."
    return 1
  fi
  log "Pull request opened for ${branch}."
}

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
# Two things --allowedTools does not do, both covered explicitly below.
#
# First, it is an auto-approve list, not a restricting allowlist -- omitted
# tools stay available and fall back to prompting, which on this unattended
# path means denied. That covers permission-gated tools (Bash, Edit, Write),
# which is why BL-0006's reasoning about git push holds. It does not cover the
# Skill tool: Claude invokes skills without a permission prompt. So skills are
# removed two ways -- --disable-slash-commands disables the feature, and a bare
# "Skill" in --disallowedTools drops the tool from the agent's context. Either
# alone would do; both are cheap and fail independently. This costs the session
# agent nothing: the nine core skills live at skills/<name>/SKILL.md, which is
# not a Claude Code discovery path, and session.md has the agent read them with
# Read rather than invoke them.
#
# Second, dev/plugins/ holds vendored third-party skills for developer sessions
# (see docs/dev-only-skills.md). They are never loaded here -- no --plugin-dir
# is passed -- but they are ordinary files in the tree, so the scoped Read deny
# keeps them out of context as prose too. Glob and Grep can still surface their
# paths and matching lines; the guarantee is that they are never loaded as
# skills, never invokable, and not readable whole.
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
    --disable-slash-commands \
    --disallowedTools "Skill" "Read(dev/plugins/**)" \
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
  # This local pass is advisory: it decides pull request vs salvage, nothing more.
  # The binding copy runs in session-validate.yml, from the base ref, where no
  # session can reach it.
  log "Validation PASSED -> pushing ${BRANCH} and opening a pull request."
  # Push first and never delete the branch. This runner's clone is ephemeral, so
  # an unpushed session is an erased session, and the branch is what the gate
  # reviews.
  if ! git push -q -u origin "$BRANCH"; then
    log "FATAL: push of ${BRANCH} rejected; work exists only on this runner."
    exit 1
  fi
  open_pull_request "$BRANCH" \
    "session ${SESSION_ID} (${MODE})" \
    "Automated research session \`${SESSION_ID}\`.

- Mode: ${MODE}
- Agent exit: ${AGENT_EXIT} (timeout=124; turn and budget limits are also nonzero)
- Runner-local validation: passed — advisory only; the required check re-runs it from the base ref.

Runner logs are attached to the workflow run as \`session-logs-*\`." \
    || exit 1
else
  log "Validation FAILED -> salvage. See $LOGDIR/validate.log"
  # Preserve the failed branch for forensics, unreviewed and unmerged.
  git push -q origin "$BRANCH:failed/${SESSION_ID}" \
    || log "WARN: could not preserve failed/${SESSION_ID} remotely."
  # Salvage ONLY narrative artifacts, onto a branch cut from main. Once the
  # ruleset requires a pull request, a direct push to main is refused for the
  # salvage exactly as it is for the session, so the salvage travels the same
  # reviewed path. Its pull request carries nothing but journals/ and HANDOFF.md,
  # which is what session-validate.yml checks for a salvage/* head.
  SALVAGE_BRANCH="salvage/${SESSION_ID}"
  git checkout -q main
  git checkout -q -b "$SALVAGE_BRANCH"
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
  if ! git push -q -u origin "$SALVAGE_BRANCH"; then
    log "FATAL: push of ${SALVAGE_BRANCH} rejected; failed/${SESSION_ID} still holds the work."
    exit 1
  fi
  open_pull_request "$SALVAGE_BRANCH" \
    "session ${SESSION_ID}: FAILED validation — journal and handoff only" \
    "Session \`${SESSION_ID}\` failed its own validation. Full branch preserved at \`failed/${SESSION_ID}\`.

This pull request carries the narrative artifacts only — \`journals/\` and \`HANDOFF.md\`. Everything else the session produced is quarantined and is not proposed for merge.

First failed check:

\`\`\`
$(grep -m1 "^FAIL" "$LOGDIR/validate.log" || echo "(see ${LOGDIR}/validate.log)")
\`\`\`" \
    || exit 1
fi

log "Session ${SESSION_ID} complete."
