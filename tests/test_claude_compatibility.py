import importlib.util
import json
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_claude_compatibility.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


compatibility = load_module("verify_claude_compatibility", SCRIPT)


class FakeClaudeCli:
    def __init__(
        self,
        *,
        launch_output: str = (
            "Starting background service…\nbackgrounded · launch-1234\n"
        ),
        malformed_after_launch: bool = False,
        stop_removes_sessions: bool = True,
        unrelated_id: str = "unrelated-0001",
        interrupt_after_launch: bool = False,
        launcher_wrong_cwd: bool = False,
        raise_during_cleanup_read: bool = False,
        duplicate_launcher_outside: bool = False,
        raise_after_stop: bool = False,
        raise_on_arguments: tuple[str, ...] | None = None,
        raise_agents_after_launch: bool = False,
        child_visible_at_launch: bool = False,
    ):
        self.binary = Path("/opt/claude-2.1.226")
        self.commands = []
        self.stopped_ids = []
        self.probe_cwd = None
        self.launch_output = launch_output
        self.malformed_after_launch = malformed_after_launch
        self.stop_removes_sessions = stop_removes_sessions
        self.interrupt_after_launch = interrupt_after_launch
        self.launcher_wrong_cwd = launcher_wrong_cwd
        self.raise_during_cleanup_read = raise_during_cleanup_read
        self.duplicate_launcher_outside = duplicate_launcher_outside
        self.raise_after_stop = raise_after_stop
        self.raise_on_arguments = raise_on_arguments
        self.raise_agents_after_launch = raise_agents_after_launch
        self.child_visible_at_launch = child_visible_at_launch
        self.active = [
            {
                "id": unrelated_id,
                "cwd": str(ROOT),
                "kind": "interactive",
                "name": "operator",
            }
        ]
        self.pending_child_id = None

    def execute(self, arguments, *, cwd, timeout_seconds):
        arguments = tuple(arguments)
        self.commands.append((arguments, cwd, timeout_seconds))
        if arguments == self.raise_on_arguments:
            raise OSError(f"simulated execution failure for {arguments}")
        if arguments == ("--version",):
            return compatibility.CommandResult(arguments, cwd, 0, "2.1.226 (Claude Code)\n")
        if arguments == ("-pd", "say ok"):
            return compatibility.CommandResult(
                arguments,
                cwd,
                1,
                "Error: Input must be provided either through stdin or as a "
                "prompt argument when using --print\n",
            )
        if arguments == ("agents", "--json"):
            if self.raise_agents_after_launch and self.probe_cwd is not None:
                raise OSError("simulated post-launch agents failure")
            if self.raise_during_cleanup_read and self.stopped_ids:
                raise OSError("simulated agents read failure")
            if self.malformed_after_launch and self.probe_cwd is not None:
                return compatibility.CommandResult(arguments, cwd, 0, "not-json")
            if self.pending_child_id is not None:
                child_id = self.pending_child_id
                self.pending_child_id = None
                self.active.append(
                    {
                        "id": child_id,
                        "cwd": str(self.probe_cwd),
                        "kind": "background",
                        "name": "--bg",
                    }
                )
            return compatibility.CommandResult(
                arguments,
                cwd,
                0,
                json.dumps(self.active),
            )
        if arguments[:1] == ("--plugin-dir",):
            self.probe_cwd = cwd
            self.active.append(
                {
                    "id": "launch-1234",
                    "cwd": str(ROOT) if self.launcher_wrong_cwd else str(cwd),
                    "kind": "background",
                    "name": "--bg",
                }
            )
            if self.duplicate_launcher_outside:
                self.active.append(
                    {
                        "id": "launch-1234",
                        "cwd": str(ROOT),
                        "kind": "background",
                        "name": "--bg",
                    }
                )
            if self.child_visible_at_launch:
                self.active.append(
                    {
                        "id": "agent-5678",
                        "cwd": str(cwd),
                        "kind": "background",
                        "name": "--bg",
                    }
                )
            if self.interrupt_after_launch:
                raise KeyboardInterrupt
            return compatibility.CommandResult(
                arguments,
                cwd,
                0,
                self.launch_output,
            )
        if arguments[:1] == ("stop",):
            session_id = arguments[1]
            self.stopped_ids.append(session_id)
            if self.stop_removes_sessions:
                self.active = [item for item in self.active if item["id"] != session_id]
            if self.stop_removes_sessions:
                if session_id == "launch-1234":
                    if not self.child_visible_at_launch:
                        self.pending_child_id = "agent-5678"
                elif session_id == "agent-5678":
                    self.pending_child_id = "agent-9999"
            if self.raise_after_stop:
                raise OSError("simulated stop transport failure")
            return compatibility.CommandResult(arguments, cwd, 0, "")
        raise AssertionError(f"Unexpected command: {arguments}")


class CompatibilityVerificationTests(unittest.TestCase):
    def test_confirmed_run_cleans_owned_sessions_and_preserves_unrelated(self):
        fake = FakeClaudeCli()
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "confirmed", report.failures)
        self.assertEqual(report.version, "2.1.226")
        self.assertTrue(report.cleanup_verified)
        self.assertEqual(report.launcher_ids, ("launch-1234",))
        self.assertEqual(
            report.owned_session_ids,
            ("launch-1234", "agent-5678", "agent-9999"),
        )
        self.assertIn("launch-1234", fake.stopped_ids)
        self.assertIn("agent-5678", fake.stopped_ids)
        self.assertIn("agent-9999", fake.stopped_ids)
        self.assertNotIn("unrelated-0001", fake.stopped_ids)
        self.assertEqual([item["id"] for item in fake.active], ["unrelated-0001"])

    def test_malformed_agents_json_after_launch_is_unverified(self):
        fake = FakeClaudeCli(malformed_after_launch=True)
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "unverified")
        self.assertFalse(report.cleanup_verified)
        self.assertIn("launch-1234", fake.stopped_ids)
        self.assertTrue(any("invalid JSON" in failure for failure in report.failures))

    def test_changed_launcher_text_still_cleans_owned_sessions(self):
        fake = FakeClaudeCli(launch_output="backgrounded service\n")
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "changed", report.failures)
        self.assertTrue(report.cleanup_verified)
        self.assertEqual(report.launcher_ids, ())
        self.assertIn("agent-5678", fake.stopped_ids)
        self.assertIn("agent-9999", fake.stopped_ids)
        self.assertEqual([item["id"] for item in fake.active], ["unrelated-0001"])

    def test_cleanup_non_convergence_is_unverified(self):
        fake = FakeClaudeCli(stop_removes_sessions=False)
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "unverified")
        self.assertFalse(report.cleanup_verified)
        self.assertTrue(
            any("did not converge" in failure for failure in report.failures),
            report.failures,
        )
        self.assertIn("launch-1234", [item["id"] for item in fake.active])

    def test_rendered_audit_records_commands_outcomes_and_owned_ids(self):
        fake = FakeClaudeCli()
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )
        rendered = compatibility.render_audit(report)

        self.assertIn("2.1.226", rendered)
        self.assertIn("/opt/claude-2.1.226", rendered)
        self.assertIn("-pd", rendered)
        self.assertIn("--plugin-dir", rendered)
        self.assertIn("exit `1`", rendered)
        self.assertIn("launch-1234", rendered)
        self.assertIn("agent-5678", rendered)
        self.assertIn("agent-9999", rendered)
        self.assertIn("Output SHA-256", rendered)
        self.assertIn("Input must be provided", rendered)
        self.assertIn("backgrounded · launch-1234", rendered)
        self.assertGreaterEqual(
            rendered.count("cleanup read owned ids: none"),
            compatibility.REQUIRED_EMPTY_POLLS,
        )
        self.assertNotIn("unrelated-0001", rendered)

    def test_launcher_id_collision_does_not_stop_preexisting_session(self):
        fake = FakeClaudeCli(unrelated_id="launch-1234")
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "unverified")
        self.assertNotIn("launch-1234", fake.stopped_ids)
        self.assertIn("launch-1234", [item["id"] for item in fake.active])

    def test_interruption_after_launch_still_cleans_owned_session(self):
        fake = FakeClaudeCli(interrupt_after_launch=True)
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "interrupted")
        self.assertTrue(report.cleanup_verified)
        self.assertIn("agent-5678", fake.stopped_ids)
        self.assertEqual([item["id"] for item in fake.active], ["unrelated-0001"])

    def test_launcher_active_outside_probe_cwd_is_not_stopped(self):
        fake = FakeClaudeCli(launcher_wrong_cwd=True)
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "unverified")
        self.assertFalse(report.cleanup_verified)
        self.assertNotIn("launch-1234", fake.stopped_ids)
        self.assertIn("launch-1234", [item["id"] for item in fake.active])

    def test_unexpected_cleanup_exception_returns_unverified_report(self):
        fake = FakeClaudeCli(raise_during_cleanup_read=True)
        before_int = signal.getsignal(signal.SIGINT)
        before_term = signal.getsignal(signal.SIGTERM)
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "unverified")
        self.assertFalse(report.cleanup_verified)
        self.assertTrue(
            any("Cleanup" in failure for failure in report.failures),
            report.failures,
        )
        self.assertIs(signal.getsignal(signal.SIGINT), before_int)
        self.assertIs(signal.getsignal(signal.SIGTERM), before_term)

    def test_duplicate_active_session_ids_are_unverified_and_not_stopped(self):
        fake = FakeClaudeCli(duplicate_launcher_outside=True)
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "unverified")
        self.assertNotIn("launch-1234", fake.stopped_ids)
        self.assertTrue(
            any("duplicate active-session id" in item for item in report.failures),
            report.failures,
        )

    def test_stop_exception_cannot_return_confirmed(self):
        fake = FakeClaudeCli(raise_after_stop=True)
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "unverified")
        self.assertTrue(report.cleanup_verified)
        self.assertTrue(
            any("could not run" in item for item in report.failures),
            report.failures,
        )

    def test_interruption_does_not_mask_cleanup_failure(self):
        fake = FakeClaudeCli(
            interrupt_after_launch=True,
            stop_removes_sessions=False,
        )
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "unverified")
        self.assertFalse(report.cleanup_verified)
        self.assertTrue(
            any("did not converge" in item for item in report.failures),
            report.failures,
        )

    def test_prelaunch_adapter_failure_returns_unverified_report(self):
        fake = FakeClaudeCli(raise_on_arguments=("--version",))
        report = compatibility.verify(fake, ROOT, sleep=lambda _: None)

        self.assertEqual(report.outcome, "unverified")
        self.assertFalse(report.cleanup_verified)
        self.assertTrue(
            any("Version lookup could not run" in item for item in report.failures),
            report.failures,
        )

    def test_postlaunch_adapter_failure_returns_unverified_report(self):
        fake = FakeClaudeCli(raise_agents_after_launch=True)
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "unverified")
        self.assertFalse(report.cleanup_verified)
        self.assertTrue(
            any("post-launch agents failure" in item for item in report.failures),
            report.failures,
        )

    def test_temp_directory_failure_returns_unverified_report(self):
        fake = FakeClaudeCli()
        with mock.patch.object(
            compatibility.tempfile,
            "mkdtemp",
            side_effect=OSError("simulated disk failure"),
        ):
            report = compatibility.verify(fake, ROOT, sleep=lambda _: None)

        self.assertEqual(report.outcome, "unverified")
        self.assertTrue(
            any("temporary probe directory" in item for item in report.failures),
            report.failures,
        )

    def test_multiple_owned_sessions_visible_at_launch_are_confirmed(self):
        fake = FakeClaudeCli(child_visible_at_launch=True)
        with tempfile.TemporaryDirectory() as temp:
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "confirmed", report.failures)
        self.assertIn("launch-1234", report.owned_session_ids)
        self.assertIn("agent-5678", report.owned_session_ids)
        self.assertTrue(report.cleanup_verified)

    def test_partial_signal_installation_is_rolled_back_and_unverified(self):
        fake = FakeClaudeCli()
        original_int = object()
        original_term = object()
        signal_calls = []

        def fake_getsignal(signum):
            return original_int if signum == signal.SIGINT else original_term

        def fake_signal(signum, handler):
            signal_calls.append((signum, handler))
            if signum == signal.SIGTERM and handler is not original_term:
                raise ValueError("simulated signal installation failure")

        with (
            mock.patch.object(compatibility.signal, "getsignal", fake_getsignal),
            mock.patch.object(compatibility.signal, "signal", fake_signal),
            tempfile.TemporaryDirectory() as temp,
        ):
            report = compatibility.verify(
                fake,
                ROOT,
                sleep=lambda _: None,
                temp_parent=Path(temp),
            )

        self.assertEqual(report.outcome, "unverified")
        self.assertIn((signal.SIGINT, original_int), signal_calls)
        self.assertFalse(any(args[0][0] == "--plugin-dir" for args in fake.commands))


if __name__ == "__main__":
    unittest.main()
