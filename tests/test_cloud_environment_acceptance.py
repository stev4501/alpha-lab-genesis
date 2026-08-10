"""Tests for the PR-only cloud-environment acceptance validator."""

import hashlib
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_cloud_environment_acceptance.py"
SPEC = importlib.util.spec_from_file_location("cloud_environment_acceptance", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TestCloudEnvironmentAcceptanceValidator(unittest.TestCase):
    def test_setup_digest_ignores_platform_trimmed_final_newline(self):
        raw = MODULE.SETUP_SCRIPT.read_bytes()
        self.assertEqual(
            MODULE.setup_script_sha256(),
            hashlib.sha256(raw.rstrip(b"\r\n")).hexdigest(),
        )

    def test_pending_receipt_fails(self):
        receipt = MODULE.pending_receipt()
        self.assertIn("status must be verified", MODULE.validate(receipt))
        self.assertFalse(receipt["firstSessionConfigPointerLoaded"])
        self.assertFalse(receipt["cachedSessionConfigPointerLoaded"])

    def test_complete_receipt_passes(self):
        receipt = MODULE.pending_receipt()
        receipt.update(
            {
                "status": "verified",
                "verifiedAt": "2026-08-09T19:00:00Z",
                "networkAccess": "Trusted",
                "setupScriptSha256": MODULE.setup_script_sha256(),
                "setupScriptDigestMatched": True,
                "firstSessionDirectInvocation": True,
                "firstSessionSubagentInvocation": True,
                "firstSessionConfigPointerLoaded": True,
                "cachedSessionDirectInvocation": True,
                "cachedSessionConfigPointerLoaded": True,
                "firstSessionUrl": "https://claude.ai/code/session/first",
                "cachedSessionUrl": "https://claude.ai/code/session/cached",
                "firstSessionSetupRan": True,
                "cachedSessionSetupSkipped": True,
            }
        )
        self.assertEqual(MODULE.validate(receipt), [])

    def test_duplicate_or_malformed_session_evidence_fails(self):
        receipt = MODULE.pending_receipt()
        receipt.update(
            {
                "status": "verified",
                "verifiedAt": "not-a-time",
                "networkAccess": "Trusted",
                "setupScriptSha256": MODULE.setup_script_sha256(),
                "setupScriptDigestMatched": True,
                "firstSessionDirectInvocation": True,
                "firstSessionSubagentInvocation": True,
                "cachedSessionDirectInvocation": True,
                "firstSessionUrl": "same",
                "cachedSessionUrl": "same",
                "firstSessionSetupRan": True,
                "cachedSessionSetupSkipped": True,
            }
        )
        errors = MODULE.validate(receipt)
        self.assertIn("session URLs must be distinct Claude session URLs", errors)
        self.assertIn("verifiedAt must be an ISO-8601 UTC timestamp", errors)

    def test_non_boolean_attestations_fail(self):
        receipt = MODULE.pending_receipt()
        receipt.update(
            {
                "status": "verified",
                "verifiedAt": "2026-08-09T19:00:00Z",
                "networkAccess": "Trusted",
                "setupScriptSha256": MODULE.setup_script_sha256(),
                "setupScriptDigestMatched": True,
                "firstSessionDirectInvocation": 1,
                "firstSessionSubagentInvocation": 1,
                "firstSessionSetupRan": 1,
                "cachedSessionDirectInvocation": 1,
                "cachedSessionSetupSkipped": 1,
                "firstSessionUrl": "https://claude.ai/code/one",
                "cachedSessionUrl": "https://claude.ai/code/two",
            }
        )
        self.assertIn(
            "firstSessionDirectInvocation must be boolean true",
            MODULE.validate(receipt),
        )

    def test_config_pointer_attestations_must_be_boolean_true(self):
        base = MODULE.pending_receipt()
        base.update(
            {
                "status": "verified",
                "verifiedAt": "2026-08-09T19:00:00Z",
                "networkAccess": "Trusted",
                "setupScriptSha256": MODULE.setup_script_sha256(),
                "setupScriptDigestMatched": True,
                "firstSessionDirectInvocation": True,
                "firstSessionSubagentInvocation": True,
                "firstSessionConfigPointerLoaded": True,
                "firstSessionSetupRan": True,
                "cachedSessionDirectInvocation": True,
                "cachedSessionConfigPointerLoaded": True,
                "cachedSessionSetupSkipped": True,
                "firstSessionUrl": "https://claude.ai/code/one",
                "cachedSessionUrl": "https://claude.ai/code/two",
            }
        )
        for field in (
            "firstSessionConfigPointerLoaded",
            "cachedSessionConfigPointerLoaded",
        ):
            for value in (False, 1, None):
                with self.subTest(field=field, value=value):
                    receipt = {**base, field: value}
                    self.assertIn(
                        f"{field} must be boolean true",
                        MODULE.validate(receipt),
                    )

    def test_changed_setup_script_digest_fails(self):
        receipt = MODULE.pending_receipt()
        receipt.update(
            {
                "status": "verified",
                "verifiedAt": "2026-08-09T19:00:00Z",
                "networkAccess": "Trusted",
                "setupScriptSha256": "0" * 64,
                "setupScriptDigestMatched": True,
                "firstSessionDirectInvocation": True,
                "firstSessionSubagentInvocation": True,
                "firstSessionSetupRan": True,
                "cachedSessionDirectInvocation": True,
                "cachedSessionSetupSkipped": True,
                "firstSessionUrl": "https://claude.ai/code/one",
                "cachedSessionUrl": "https://claude.ai/code/two",
            }
        )
        self.assertIn(
            "setupScriptSha256 must match the repository setup script",
            MODULE.validate(receipt),
        )

    def test_traversal_shaped_session_url_fails(self):
        receipt = MODULE.pending_receipt()
        receipt.update(
            {
                "status": "verified",
                "verifiedAt": "2026-08-09T19:00:00Z",
                "setupScriptDigestMatched": True,
                "firstSessionDirectInvocation": True,
                "firstSessionSubagentInvocation": True,
                "firstSessionSetupRan": True,
                "cachedSessionDirectInvocation": True,
                "cachedSessionSetupSkipped": True,
                "firstSessionUrl": "https://claude.ai/code/../not-a-session",
                "cachedSessionUrl": "https://claude.ai/code/two",
            }
        )
        self.assertIn(
            "session URLs must be distinct Claude session URLs",
            MODULE.validate(receipt),
        )

    def test_pull_request_workflow_runs_validator(self):
        workflow = (
            ROOT / ".github" / "workflows" / "cloud-environment-acceptance.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "python scripts/validate_cloud_environment_acceptance.py",
            workflow,
        )
        self.assertNotIn("paths:", workflow)


if __name__ == "__main__":
    unittest.main()
