#!/usr/bin/env python3
"""Validate the protected receipt used by the PR-only cloud plugin gate."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / ".claude" / "cloud-plugin-acceptance.json"
PLUGIN_ID = "mattpocock-skills@alpha-lab-pinned"
UPSTREAM_SHA = "84fdeffd12f2ee307994d1eb6feb48173b6e0502"
CLAUDE_VERSION = "2.1.226"


def validate(receipt):
    errors = []
    expected = {
        "pluginId": PLUGIN_ID,
        "gitCommitSha": UPSTREAM_SHA,
        "claudeVersion": CLAUDE_VERSION,
        "directSkillInvocation": True,
        "subagentSkillInvocation": True,
    }

    if receipt.get("status") != "verified":
        errors.append("status must be verified")
    for field, value in expected.items():
        if receipt.get(field) != value:
            errors.append(f"{field} must equal {value!r}")
    for field in ("cloudEnvironment", "sessionUrl", "verifiedAt"):
        if not receipt.get(field):
            errors.append(f"{field} must be recorded")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", nargs="?", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args()

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    errors = validate(receipt)
    if errors:
        for error in errors:
            print(f"cloud plugin acceptance: {error}")
        return 1

    print("cloud plugin acceptance: verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
