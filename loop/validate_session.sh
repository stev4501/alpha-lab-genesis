#!/usr/bin/env bash
# validate_session.sh <base> <branch> <session_id>
# The commit gate for autonomous sessions in alpha-lab-genesis.
# Every check prints PASS or FAIL; the script exits non-zero if any check fails.
#
# Fail-closed: if either git ref does not resolve, print FAIL and exit
# immediately without running any other check. A validator that silently
# passes on a broken diff is worse than none.

set -uo pipefail

# Sealed-component hashes are verified against CORE_MANIFEST.json as it exists
# at this human-tagged reference commit — never against the session's working
# tree — so an agent that edits a sealed file and its manifest entry together
# still fails. Update only when a human tags a successor generation.
REFERENCE_TAG="pre-mvp-freeze"

if [[ $# -ne 3 ]]; then
  echo "FAIL: usage: validate_session.sh <base> <branch> <session_id>"
  exit 1
fi
BASE="$1"; BRANCH="$2"; SESSION_ID="$3"
FAILED=0

# 0. Fail closed on unresolvable refs.
for ref in "$BASE" "$BRANCH" "$REFERENCE_TAG"; do
  if ! git rev-parse --verify -q "$ref^{commit}" >/dev/null; then
    echo "FAIL: ref does not resolve: $ref — refusing to validate"
    exit 1
  fi
done

# 1. Protected paths untouched by the session branch.
PROTECTED='^(evaluator/|scripts/|schemas/|loop/|\.github/|\.claude/|CORE_MANIFEST\.json$|MISSION\.md$|CONTEXT\.md$|CODEOWNERS$)'
if git diff --name-only "$BASE".."$BRANCH" | grep -qE "$PROTECTED"; then
  echo "FAIL: protected paths modified:"
  git diff --name-only "$BASE".."$BRANCH" | grep -E "$PROTECTED" | sed 's/^/  /'
  FAILED=1
else
  echo "PASS: protected paths untouched"
fi

# 2. EXPERIMENTS.jsonl append-only: base version is a byte-prefix of branch version.
if git cat-file -e "$BASE:EXPERIMENTS.jsonl" 2>/dev/null; then
  OLD_SIZE=$(git cat-file -s "$BASE:EXPERIMENTS.jsonl")
  NEW_SIZE=$(git cat-file -s "$BRANCH:EXPERIMENTS.jsonl" 2>/dev/null || echo 0)
  if [[ "$NEW_SIZE" -ge "$OLD_SIZE" ]] \
     && git show "$BRANCH:EXPERIMENTS.jsonl" | head -c "$OLD_SIZE" \
        | cmp -s - <(git show "$BASE:EXPERIMENTS.jsonl"); then
    echo "PASS: EXPERIMENTS.jsonl append-only"
  else
    echo "FAIL: EXPERIMENTS.jsonl rewritten (base is not a byte-prefix of branch)"
    FAILED=1
  fi
else
  echo "FAIL: EXPERIMENTS.jsonl missing on base ref"
  FAILED=1
fi

# 3. Existing results/ immutable: every file present on base is byte-identical
#    on the branch. New result directories are permitted.
RESULTS_OK=1
while IFS= read -r f; do
  if ! git cat-file -e "$BRANCH:$f" 2>/dev/null; then
    echo "FAIL: results file deleted on branch: $f"
    RESULTS_OK=0
  elif [[ "$(git rev-parse "$BASE:$f")" != "$(git rev-parse "$BRANCH:$f")" ]]; then
    echo "FAIL: results file modified on branch: $f"
    RESULTS_OK=0
  fi
done < <(git ls-tree -r --name-only "$BASE" -- results/)
if [[ "$RESULTS_OK" -eq 1 ]]; then
  echo "PASS: existing results/ files byte-identical"
else
  FAILED=1
fi

# 4. STATE.json validates against schemas/state.schema.json (both from branch).
STATE_TMP=$(mktemp -d)
git show "$BRANCH:STATE.json" > "$STATE_TMP/STATE.json" 2>/dev/null
git show "$BRANCH:schemas/state.schema.json" > "$STATE_TMP/state.schema.json" 2>/dev/null
if python - "$STATE_TMP" <<'PYEOF' >/dev/null 2>&1
import json, sys
try:
    import jsonschema
except ImportError:
    sys.exit(2)
base = sys.argv[1]
with open(f"{base}/STATE.json", encoding="utf-8") as fh:
    state = json.load(fh)
with open(f"{base}/state.schema.json", encoding="utf-8") as fh:
    schema = json.load(fh)
jsonschema.validate(state, schema)
PYEOF
then
  echo "PASS: STATE.json validates against schemas/state.schema.json"
else
  echo "FAIL: STATE.json schema validation failed (or jsonschema unavailable)"
  FAILED=1
fi
rm -rf "$STATE_TMP"

# 5. Sealed-component hashes: CORE_MANIFEST.json is read from the reference
#    tag, and each sealed path on the BRANCH must hash to the value the
#    reference manifest records.
SEALED_OUT=$(python - "$REFERENCE_TAG" "$BRANCH" <<'PYEOF'
import hashlib, json, subprocess, sys
reference, branch = sys.argv[1], sys.argv[2]
proc = subprocess.run(
    ["git", "show", f"{reference}:CORE_MANIFEST.json"], capture_output=True
)
if proc.returncode != 0:
    print(f"cannot read CORE_MANIFEST.json at reference {reference}")
    sys.exit(1)
manifest = json.loads(proc.stdout)
failed = False
for component in manifest.get("sealed_components", []):
    for entry in component.get("paths", []):
        path, expected = entry["path"], entry["sha256"]
        proc = subprocess.run(
            ["git", "show", f"{branch}:{path}"], capture_output=True
        )
        if proc.returncode != 0:
            print(f"missing sealed path on branch: {path}")
            failed = True
            continue
        actual = hashlib.sha256(proc.stdout).hexdigest()
        if actual != expected:
            print(f"sealed hash mismatch vs {path}: expected {expected}, got {actual}")
            failed = True
sys.exit(1 if failed else 0)
PYEOF
)
if [[ $? -eq 0 ]]; then
  echo "PASS: sealed-component hashes verify against reference tag ${REFERENCE_TAG}"
else
  echo "FAIL: sealed-component hash verification against reference tag ${REFERENCE_TAG}:"
  echo "$SEALED_OUT" | sed 's/^/  /'
  FAILED=1
fi

# 6. Repository contract validator exits zero (run against the checked-out tree).
if python scripts/validate_repository.py >/dev/null 2>&1; then
  echo "PASS: scripts/validate_repository.py"
else
  echo "FAIL: scripts/validate_repository.py"
  FAILED=1
fi

# 7. Test suite passes.
if python -m pytest tests -q >/dev/null 2>&1; then
  echo "PASS: pytest tests"
else
  echo "FAIL: pytest tests"
  FAILED=1
fi

# 8. Handoff artifact updated this session.
if git diff --quiet "$BASE".."$BRANCH" -- HANDOFF.md; then
  echo "FAIL: HANDOFF.md not updated"
  FAILED=1
else
  echo "PASS: HANDOFF.md updated"
fi

# 9. Journal entry exists for this session ID.
if git diff --name-only --diff-filter=A "$BASE".."$BRANCH" -- journals/ | grep -q "$SESSION_ID"; then
  echo "PASS: journal entry for ${SESSION_ID}"
else
  echo "FAIL: no journal entry for ${SESSION_ID}"
  FAILED=1
fi

exit "$FAILED"
