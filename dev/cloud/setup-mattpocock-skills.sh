#!/usr/bin/env bash
# Paste this complete script into the Claude Code cloud environment Setup script.
# Also set CLAUDE_CONFIG_DIR=/opt/alpha-lab-dev/claude-config in that environment.

set -euo pipefail
umask 022
# Fail closed, but never key a guard to environment-dependent decoration such
# as Unicode status glyphs. A false positive here prevents the environment from
# starting at all.

CLOUD_ROOT="/opt/alpha-lab-dev"

EXPECTED_CONFIG_DIR="${CLOUD_ROOT}/claude-config"
USER_MEMORY_FILE="${EXPECTED_CONFIG_DIR}/CLAUDE.md"
MARKETPLACE_DIR="${CLOUD_ROOT}/marketplace"
MARKETPLACE_FILE="${MARKETPLACE_DIR}/.claude-plugin/marketplace.json"
if [[ -n "${CLAUDE_CONFIG_DIR:-}" && "$CLAUDE_CONFIG_DIR" != "$EXPECTED_CONFIG_DIR" ]]; then
  echo "CLAUDE_CONFIG_DIR must equal ${EXPECTED_CONFIG_DIR}" >&2
  exit 2
fi
# Cloud environment variables are applied to the later Claude process but were
# not present in the pre-launch setup process during acceptance run 1. Export
# the same fixed path here so setup and runtime converge without relying on
# lifecycle ordering.
export CLAUDE_CONFIG_DIR="$EXPECTED_CONFIG_DIR"
for path in \
  "$CLOUD_ROOT" \
  "$CLAUDE_CONFIG_DIR" \
  "$USER_MEMORY_FILE" \
  "$MARKETPLACE_DIR" \
  "$MARKETPLACE_DIR/.claude-plugin" \
  "$MARKETPLACE_FILE"
do
  if [[ -L "$path" ]]; then
    echo "refusing symlinked setup path: $path" >&2
    exit 2
  fi
done

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
MARKETPLACE_NAME="alpha-lab-pinned"
PLUGIN_ID="mattpocock-skills@alpha-lab-pinned"
UPSTREAM_SHA="84fdeffd12f2ee307994d1eb6feb48173b6e0502"

for dependency in "$CLAUDE_BIN" git python3; do
  command -v "$dependency" >/dev/null
done
mkdir -p "$CLAUDE_CONFIG_DIR" "$MARKETPLACE_DIR/.claude-plugin"

MEMORY_TMP="$(mktemp "$CLAUDE_CONFIG_DIR/.CLAUDE.md.XXXXXX")"
trap 'rm -f "$MEMORY_TMP"' EXIT
cat > "$MEMORY_TMP" <<'MARKDOWN'
# Alpha Lab Dev cloud environment

This environment is for supervised development sessions.

When the current repository contains `docs/agents/session-prompt.md`, read and
follow that file before invoking a Matt Pocock engineering skill. It points the
skills at the repository's issue tracker, triage vocabulary, and domain docs
without placing those instructions in project memory that the autonomous loop
would also read.

The autonomous research workflow is launched by `loop/run_session.sh`. It does
not use this cloud environment, and this user-level memory does not authorize
changing that separation.
MARKDOWN
chmod 0644 "$MEMORY_TMP"
mv -fT "$MEMORY_TMP" "$USER_MEMORY_FILE"
MEMORY_TMP=""
trap - EXIT

MARKETPLACE_TMP="$(mktemp "$MARKETPLACE_DIR/.claude-plugin/.marketplace.json.XXXXXX")"
trap 'rm -f "$MARKETPLACE_TMP"' EXIT
cat > "$MARKETPLACE_TMP" <<'JSON'
{
  "name": "alpha-lab-pinned",
  "owner": {
    "name": "Alpha Lab"
  },
  "plugins": [
    {
      "name": "mattpocock-skills",
      "description": "Pinned developer-only engineering skills for Alpha Lab",
      "source": {
        "source": "url",
        "url": "https://github.com/mattpocock/skills.git",
        "sha": "84fdeffd12f2ee307994d1eb6feb48173b6e0502"
      }
    }
  ]
}
JSON
mv -fT "$MARKETPLACE_TMP" "$MARKETPLACE_FILE"
MARKETPLACE_TMP=""
trap - EXIT

# Re-register from the cache-stable local path. Only the version-tested
# first-run "not found" result is allowed to miss.
set +e
REMOVE_OUTPUT="$(
  "$CLAUDE_BIN" plugin marketplace remove "$MARKETPLACE_NAME" --scope user 2>&1
)"
REMOVE_STATUS=$?
set -e
if (( REMOVE_STATUS != 0 )); then
  EXPECTED_REMOVE_MESSAGE="Failed to remove marketplace: Marketplace '${MARKETPLACE_NAME}' not found"
  if [[ "$REMOVE_OUTPUT" != *"$EXPECTED_REMOVE_MESSAGE" ]]; then
    echo "$REMOVE_OUTPUT" >&2
    exit "$REMOVE_STATUS"
  fi
fi
"$CLAUDE_BIN" plugin marketplace add "$MARKETPLACE_DIR" --scope user
"$CLAUDE_BIN" plugin install "$PLUGIN_ID" --scope user
if ! ENABLE_OUTPUT="$("$CLAUDE_BIN" plugin enable "$PLUGIN_ID" --scope user 2>&1)"; then
  if [[ "$ENABLE_OUTPUT" != *"already enabled"* ]]; then
    echo "$ENABLE_OUTPUT" >&2
    exit 1
  fi
fi

PLUGIN_LIST_JSON="$("$CLAUDE_BIN" plugin list --json)"
export PLUGIN_LIST_JSON PLUGIN_ID
python3 - "$CLAUDE_CONFIG_DIR/plugins/installed_plugins.json" "$UPSTREAM_SHA" <<'PY'
import json
import os
import pathlib
import sys

installed_path = pathlib.Path(sys.argv[1])
expected_sha = sys.argv[2]
plugin_id = os.environ["PLUGIN_ID"]
config_root = pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"])
cache_root_lexical = config_root / "plugins" / "cache"

for path in (config_root, config_root / "plugins", cache_root_lexical):
    if path.is_symlink():
        raise SystemExit(f"refusing symlinked plugin-cache path: {path}")
cache_root_resolved = cache_root_lexical.resolve(strict=True)


def secure_install_path(value):
    if not isinstance(value, str) or not value:
        return None
    path = pathlib.Path(value)
    if not path.is_absolute():
        return None
    try:
        relative = path.relative_to(cache_root_lexical)
    except ValueError:
        return None

    current = cache_root_lexical
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return None
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(cache_root_resolved)
    except (FileNotFoundError, RuntimeError, ValueError):
        return None
    if not resolved.is_dir():
        return None
    return str(resolved)

installed = json.loads(installed_path.read_text(encoding="utf-8"))
records = installed.get("plugins", {}).get(plugin_id) or []
plugins = json.loads(os.environ["PLUGIN_LIST_JSON"])
enabled = [
    plugin
    for plugin in plugins
    if plugin.get("id") == plugin_id and plugin.get("enabled") is True
]
if not enabled:
    raise SystemExit(f"{plugin_id} is missing or disabled")

pinned_paths = {
    secure_install_path(record.get("installPath"))
    for record in records
    if (
        record.get("gitCommitSha") == expected_sha
        and secure_install_path(record.get("installPath")) is not None
    )
}
if not pinned_paths:
    actual = [record.get("gitCommitSha") for record in records]
    raise SystemExit(f"{plugin_id} SHA mismatch: expected {expected_sha}, got {actual}")
if not any(
    secure_install_path(plugin.get("installPath")) in pinned_paths
    for plugin in enabled
):
    raise SystemExit(f"enabled {plugin_id} is not the install pinned to {expected_sha}")
PY

echo "cloud developer plugin verified: ${PLUGIN_ID}@${UPSTREAM_SHA}"
