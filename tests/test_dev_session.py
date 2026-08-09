"""Tests for bin/dev-session.

The script was bash until it grew a flag-class guard, a config pointer, and its
own failure modes — at which point every assertion had to go through a
subprocess with a stubbed CLAUDE_BIN. It is Python now so the rules can be
tested directly, which is what lets the flag table below be exhaustive rather
than representative.

Loaded with importlib because the entry point is `bin/dev-session`, with no
`.py` suffix. Same helper shape as tests/test_repository.py.
"""

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "dev-session"


def load_module(name: str, path: Path):
    """Same shape as tests/test_repository.py, with one difference.

    `bin/dev-session` has no `.py` suffix, so spec_from_file_location cannot
    infer a loader and returns None. The loader is supplied explicitly instead.
    """
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


dev_session = load_module("dev_session", SCRIPT)


class TestRefusalRules(unittest.TestCase):
    """Which argument forms reach an unattended session.

    Every entry here is a form that was either found to be a live bypass during
    review or is a near-miss that a naive guard would catch by mistake. See
    docs/dev-only-skills.md for the evidence behind each.
    """

    REFUSED = [
        ("-p", "the literal short flag"),
        ("--print", "the literal long flag"),
        ("--print=true", "rejected by the CLI too, covered so we do not depend on that"),
        ("-pd", "clustered short flags engage --print"),
        ("-dp", "cluster order does not matter"),
        ("-pv", "any cluster containing p"),
        ("--bg", "background agent, runs locally with nobody watching"),
        ("--background", "long form of the same"),
        ("--bg=x", "with a value"),
        ("--cloud", "cloud session"),
        ("--cloud=desc", "with a description"),
        ("--remote", "deprecated alias of --cloud, absent from claude --help"),
        ("--remote=task", "with a value"),
    ]

    ALLOWED = [
        ("--permission-mode", "long flag with a leading p — must not trip the cluster rule"),
        ("--model", "ordinary long flag"),
        ("--debug", "ordinary long flag"),
        ("-d", "short flag without p"),
        ("-c", "short flag without p"),
        ("-w", "short flag without p"),
        ("--add-dir", "ordinary long flag"),
        ("--agent", "ordinary long flag"),
        ("--remote-control", "documented as interactive; --remote must not catch it"),
        ("--rc", "its alias, likewise"),
        ("--", "not a flag we refuse, and not an end-of-options marker either"),
        ("explain the -p flag", "positional text mentioning a refused flag"),
        ("/mattpocock-skills:tdd", "a skill invocation"),
    ]

    def test_refused_forms(self):
        for arg, why in self.REFUSED:
            with self.subTest(arg=arg, why=why):
                self.assertIsNotNone(
                    dev_session.refusal_reason(arg), f"{arg} should be refused ({why})"
                )

    def test_allowed_forms(self):
        for arg, why in self.ALLOWED:
            with self.subTest(arg=arg, why=why):
                self.assertIsNone(
                    dev_session.refusal_reason(arg), f"{arg} should be allowed ({why})"
                )

    def test_end_of_options_marker_does_not_stop_the_scan(self):
        """`claude -- --bg` starts a background session, so `--` cannot end the scan.

        Verified against Claude Code 2.1.226 — the marker is not honoured for
        these flags. Treating it conventionally here would restore the bypass.
        """
        self.assertIsNotNone(dev_session.first_refusal(["--", "--bg"]))
        self.assertIsNotNone(dev_session.first_refusal(["--bg", "--", "x"]))
        self.assertIsNone(dev_session.first_refusal(["--", "some prompt"]))

    def test_first_refusal_reports_the_offending_argument(self):
        found = dev_session.first_refusal(["--model", "sonnet", "--bg", "-p"])
        self.assertIsNotNone(found)
        self.assertEqual(found[0], "--bg", "should report the first offender, not the last")

    def test_no_refusal_for_an_ordinary_invocation(self):
        self.assertIsNone(dev_session.first_refusal(["--model", "sonnet", "/tdd"]))


class TestArgvConstruction(unittest.TestCase):
    """Both flags must be emitted: one loads the skills, one configures them."""

    def test_both_flags_are_emitted_with_absolute_paths(self):
        argv = dev_session.build_argv("claude", Path("/repo"), ["--model", "sonnet"])
        self.assertEqual(argv[0], "claude")
        self.assertIn("--plugin-dir", argv)
        self.assertIn("--append-system-prompt-file", argv)
        self.assertEqual(
            argv[argv.index("--plugin-dir") + 1], "/repo/dev/plugins/mattpocock-skills"
        )
        self.assertEqual(
            argv[argv.index("--append-system-prompt-file") + 1],
            "/repo/docs/agents/session-prompt.md",
        )

    def test_user_arguments_come_last(self):
        """So a user flag can override anything the wrapper sets."""
        argv = dev_session.build_argv("claude", Path("/repo"), ["--model", "sonnet"])
        self.assertEqual(argv[-2:], ["--model", "sonnet"])

    def test_no_user_arguments_is_valid(self):
        argv = dev_session.build_argv("claude", Path("/repo"), [])
        self.assertEqual(argv[-2], "--append-system-prompt-file")


class TestPathChecks(unittest.TestCase):
    """Starting without the plugin or without the pointer are both failures."""

    def test_real_repository_passes(self):
        self.assertEqual(dev_session.check_paths(ROOT), [])

    def test_missing_plugin_manifest_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            problems = dev_session.check_paths(Path(tmp))
        self.assertTrue(any("plugin directory" in p for p in problems))

    def test_missing_config_pointer_is_reported(self):
        """A session that loads the skills without their config is a failure, not a warning."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / dev_session.PLUGIN_DIRS[0] / ".claude-plugin"
            manifest.mkdir(parents=True)
            (manifest / "plugin.json").write_text("{}", encoding="utf-8")
            problems = dev_session.check_paths(root)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("session-prompt.md", problems[0])


class TestEndToEnd(unittest.TestCase):
    """A few real runs, because the unit tests above never exec anything."""

    def _run(self, *args, claude_bin="/bin/false"):
        env = {**os.environ, "CLAUDE_BIN": claude_bin}
        return subprocess.run(
            [str(SCRIPT), *args],
            capture_output=True, text=True, cwd=ROOT, env=env, timeout=30,
        )

    def test_refused_invocation_exits_two_and_prints_the_direct_command(self):
        result = self._run("-p", "noop")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("refusing", result.stderr)
        # The message must carry BOTH flags, or it teaches an unconfigured route.
        self.assertIn("--plugin-dir", result.stderr)
        self.assertIn("--append-system-prompt-file", result.stderr)

    def test_ordinary_invocation_reaches_the_binary(self):
        result = self._run("--model", "sonnet", claude_bin="/bin/true")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_emitted_argv_carries_the_pointer_and_it_names_every_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "argv"
            stub = Path(tmp) / "stub"
            stub.write_text(
                f'#!/usr/bin/env bash\nprintf "%s\\n" "$@" > {log}\n', encoding="utf-8"
            )
            stub.chmod(0o755)
            result = self._run("--model", "sonnet", claude_bin=str(stub))
            self.assertEqual(result.returncode, 0, result.stderr)
            argv = log.read_text(encoding="utf-8").splitlines()

        self.assertIn("--plugin-dir", argv)
        self.assertIn("--append-system-prompt-file", argv)
        pointer = Path(argv[argv.index("--append-system-prompt-file") + 1])
        self.assertTrue(pointer.is_file(), f"pointer file missing: {pointer}")
        text = pointer.read_text(encoding="utf-8")
        for config in ("issue-tracker.md", "triage-labels.md", "domain.md"):
            with self.subTest(config=config):
                self.assertIn(config, text, f"pointer does not name {config}")


if __name__ == "__main__":
    unittest.main()
