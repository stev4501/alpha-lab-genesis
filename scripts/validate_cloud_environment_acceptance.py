#!/usr/bin/env python3
"""Validate the protected cloud-environment plugin acceptance receipt."""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import posixpath
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / ".claude" / "cloud-environment-plugin-acceptance.json"
SETUP_SCRIPT = ROOT / "dev" / "cloud" / "setup-mattpocock-skills.sh"
ENVIRONMENT_NAME = "Alpha Lab Dev"
CONFIG_DIR = "/opt/alpha-lab-dev/claude-config"
PLUGIN_ID = "mattpocock-skills@alpha-lab-pinned"
UPSTREAM_SHA = "84fdeffd12f2ee307994d1eb6feb48173b6e0502"
CLAUDE_VERSION = "2.1.226"


def setup_script_sha256():
    # Claude's environment editor trims trailing newlines. Hash the executable
    # content rather than textarea EOF normalization.
    return hashlib.sha256(SETUP_SCRIPT.read_bytes().rstrip(b"\r\n")).hexdigest()


def pending_receipt():
    return {
        "status": "pending",
        "environmentName": ENVIRONMENT_NAME,
        "configDir": CONFIG_DIR,
        "pluginId": PLUGIN_ID,
        "gitCommitSha": UPSTREAM_SHA,
        "claudeVersion": CLAUDE_VERSION,
        "networkAccess": "Trusted",
        "setupScriptSha256": setup_script_sha256(),
        "setupScriptDigestMatched": False,
        "firstSessionDirectInvocation": False,
        "firstSessionSubagentInvocation": False,
        "firstSessionSetupRan": False,
        "cachedSessionDirectInvocation": False,
        "cachedSessionSetupSkipped": False,
        "firstSessionUrl": "",
        "cachedSessionUrl": "",
        "verifiedAt": "",
    }


def validate(receipt):
    errors = []
    expected = {
        "environmentName": ENVIRONMENT_NAME,
        "configDir": CONFIG_DIR,
        "pluginId": PLUGIN_ID,
        "gitCommitSha": UPSTREAM_SHA,
        "claudeVersion": CLAUDE_VERSION,
        "networkAccess": "Trusted",
    }
    boolean_fields = (
        "firstSessionDirectInvocation",
        "firstSessionSubagentInvocation",
        "firstSessionSetupRan",
        "cachedSessionDirectInvocation",
        "cachedSessionSetupSkipped",
        "setupScriptDigestMatched",
    )

    if receipt.get("status") != "verified":
        errors.append("status must be verified")
    for field, value in expected.items():
        if receipt.get(field) != value:
            errors.append(f"{field} must equal {value!r}")
    for field in boolean_fields:
        if type(receipt.get(field)) is not bool or receipt.get(field) is not True:
            errors.append(f"{field} must be boolean true")
    if receipt.get("setupScriptSha256") != setup_script_sha256():
        errors.append("setupScriptSha256 must match the repository setup script")

    first_url = receipt.get("firstSessionUrl")
    cached_url = receipt.get("cachedSessionUrl")

    def canonical_session(url):
        if not isinstance(url, str):
            return None
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if parsed.scheme != "https" or parsed.netloc != "claude.ai":
            return None
        if not path.startswith("/code/") or len(path) <= len("/code/"):
            return None
        if "%" in path or posixpath.normpath(path) != path:
            return None
        return path

    first_session = canonical_session(first_url)
    cached_session = canonical_session(cached_url)
    if not first_session or not cached_session or first_session == cached_session:
        errors.append("session URLs must be distinct Claude session URLs")

    verified_at = receipt.get("verifiedAt")
    try:
        if not isinstance(verified_at, str) or not verified_at.endswith("Z"):
            raise ValueError
        parsed = datetime.datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
        if parsed.tzinfo != datetime.timezone.utc:
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        errors.append("verifiedAt must be an ISO-8601 UTC timestamp")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", nargs="?", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    errors = validate(receipt)
    if errors:
        for error in errors:
            print(f"cloud environment acceptance: {error}")
        return 1
    print("cloud environment acceptance: verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
