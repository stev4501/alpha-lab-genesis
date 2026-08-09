"""Tests for the PR-only cloud plugin acceptance gate."""

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_cloud_plugin_acceptance.py"
SPEC = importlib.util.spec_from_file_location("cloud_acceptance", SCRIPT)
CLOUD_ACCEPTANCE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CLOUD_ACCEPTANCE)


class TestCloudPluginAcceptanceValidator(unittest.TestCase):
    def test_pending_receipt_fails_pr_gate(self):
        receipt = {
            "status": "pending",
            "pluginId": CLOUD_ACCEPTANCE.PLUGIN_ID,
            "gitCommitSha": CLOUD_ACCEPTANCE.UPSTREAM_SHA,
            "claudeVersion": CLOUD_ACCEPTANCE.CLAUDE_VERSION,
            "cloudEnvironment": "",
            "sessionUrl": "",
            "verifiedAt": "",
            "directSkillInvocation": False,
            "subagentSkillInvocation": False,
        }
        self.assertIn("status must be verified", CLOUD_ACCEPTANCE.validate(receipt))

    def test_complete_verified_receipt_passes_pr_gate(self):
        receipt = {
            "status": "verified",
            "pluginId": CLOUD_ACCEPTANCE.PLUGIN_ID,
            "gitCommitSha": CLOUD_ACCEPTANCE.UPSTREAM_SHA,
            "claudeVersion": CLOUD_ACCEPTANCE.CLAUDE_VERSION,
            "cloudEnvironment": "Default",
            "sessionUrl": "https://claude.ai/code/session/example",
            "verifiedAt": "2026-08-09T18:00:00Z",
            "directSkillInvocation": True,
            "subagentSkillInvocation": True,
        }
        self.assertEqual(CLOUD_ACCEPTANCE.validate(receipt), [])

    def test_pull_request_workflow_runs_the_gate(self):
        workflow = (
            ROOT / ".github" / "workflows" / "cloud-plugin-acceptance.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("python scripts/validate_cloud_plugin_acceptance.py", workflow)


if __name__ == "__main__":
    unittest.main()
