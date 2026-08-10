"""Contract tests for the cloud-environment developer-skill installer."""

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "dev" / "cloud" / "setup-mattpocock-skills.sh"
ACCEPTANCE = ROOT / ".claude" / "cloud-environment-plugin-acceptance.json"
PLUGIN_ID = "mattpocock-skills@alpha-lab-pinned"
UPSTREAM_SHA = "84fdeffd12f2ee307994d1eb6feb48173b6e0502"


class TestCloudEnvironmentSetup(unittest.TestCase):
    def make_fake_claude(self, root):
        fake = root / "claude"
        fake.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import json
                import os
                import pathlib
                import sys

                args = sys.argv[1:]
                config = pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"])
                log = pathlib.Path(os.environ["FAKE_CLAUDE_LOG"])
                with log.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(args) + "\\n")

                if args[:3] == ["plugin", "marketplace", "remove"]:
                    if os.environ.get("FAKE_REMOVE_ERROR"):
                        print(
                            "temporary backend failure: target not found in cache",
                            file=sys.stderr,
                        )
                    else:
                        print(
                            "× Failed to remove marketplace: Marketplace "
                            "'alpha-lab-pinned' not found",
                            file=sys.stderr,
                        )
                    raise SystemExit(1)
                if args[:3] == ["plugin", "marketplace", "add"]:
                    raise SystemExit(0)
                if args[:2] == ["plugin", "install"]:
                    cache_root = config / "plugins" / "cache"
                    cache_root.mkdir(parents=True, exist_ok=True)
                    install_path = cache_root / "plugin"
                    path_mode = os.environ.get("FAKE_PATH_MODE")
                    if path_mode == "leaf-symlink":
                        target_path = config / "plugins" / "cache" / "real-plugin"
                        target_path.mkdir(parents=True, exist_ok=True)
                        install_path.parent.mkdir(parents=True, exist_ok=True)
                        install_path.symlink_to(target_path, target_is_directory=True)
                    elif path_mode == "ancestor-symlink":
                        outside = config.parent / "outside-cache"
                        target_path = outside / "plugin"
                        target_path.mkdir(parents=True, exist_ok=True)
                        alias = config / "plugins" / "cache" / "alias"
                        alias.parent.mkdir(parents=True, exist_ok=True)
                        alias.symlink_to(outside, target_is_directory=True)
                        install_path = alias / "plugin"
                    elif path_mode == "outside-root":
                        install_path = config.parent / "outside-plugin"
                        install_path.mkdir(parents=True, exist_ok=True)
                    else:
                        install_path.mkdir(parents=True, exist_ok=True)
                    target = config / "plugins" / "installed_plugins.json"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    (config / "plugins" / "fake_install_path").write_text(
                        str(install_path),
                        encoding="utf-8",
                    )
                    target.write_text(json.dumps({{
                        "version": 2,
                        "plugins": {{
                            "{PLUGIN_ID}": [{{
                                "scope": "user",
                                "installPath": (
                                    None
                                    if os.environ.get("FAKE_MISSING_PATHS")
                                    else str(install_path)
                                ),
                                "version": "1.2.3",
                                "gitCommitSha": "{UPSTREAM_SHA}"
                            }}]
                        }}
                    }}), encoding="utf-8")
                    raise SystemExit(0)
                if args[:2] == ["plugin", "enable"]:
                    raise SystemExit(0)
                if args[:2] == ["plugin", "list"]:
                    install_path = (
                        config / "plugins" / "fake_install_path"
                    ).read_text(encoding="utf-8")
                    print(json.dumps([{{
                        "id": "{PLUGIN_ID}",
                        "enabled": True,
                        "version": "1.2.3",
                        "installPath": (
                            None
                            if os.environ.get("FAKE_MISSING_PATHS")
                            else install_path
                        )
                    }}]))
                    raise SystemExit(0)
                raise SystemExit(2)
                """
            ),
            encoding="utf-8",
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        return fake

    def make_setup_copy(self, root):
        """Create a test-only copy whose fixed production root points at temp."""
        setup = root / "setup-mattpocock-skills.sh"
        text = SETUP.read_text(encoding="utf-8")
        expected = 'CLOUD_ROOT="/opt/alpha-lab-dev"'
        self.assertIn(expected, text)
        setup.write_text(
            text.replace(expected, f'CLOUD_ROOT="{root / "alpha-lab-dev"}"', 1),
            encoding="utf-8",
        )
        setup.chmod(setup.stat().st_mode | stat.S_IXUSR)
        return setup

    def test_setup_uses_fixed_config_when_environment_variable_is_not_injected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = self.make_fake_claude(root)
            setup = self.make_setup_copy(root)
            env = {
                **{
                    k: v
                    for k, v in os.environ.items()
                    if k != "CLAUDE_CONFIG_DIR"
                },
                "CLAUDE_BIN": str(fake),
                "FAKE_CLAUDE_LOG": str(root / "claude.log"),
            }
            result = subprocess.run(
                ["bash", str(setup)],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("verified", result.stdout)

    def test_mismatched_config_directory_is_rejected(self):
        result = subprocess.run(
            ["bash", str(SETUP)],
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_CONFIG_DIR": "/tmp/wrong-config"},
            timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CLAUDE_CONFIG_DIR must equal", result.stderr)

    def test_setup_registers_installs_and_verifies_idempotently(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = self.make_fake_claude(root)
            setup = self.make_setup_copy(root)
            test_root = root / "alpha-lab-dev"
            config = test_root / "claude-config"
            log = root / "claude.log"
            env = {
                **os.environ,
                "CLAUDE_BIN": str(fake),
                "CLAUDE_CONFIG_DIR": str(config),
                "FAKE_CLAUDE_LOG": str(log),
            }

            for _ in range(2):
                result = subprocess.run(
                    ["bash", str(setup)],
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("verified", result.stdout)

            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertIn(
                ["plugin", "install", PLUGIN_ID, "--scope", "user"],
                calls,
            )
            self.assertIn(
                ["plugin", "enable", PLUGIN_ID, "--scope", "user"],
                calls,
            )
            self.assertIn(["plugin", "list", "--json"], calls)

            installed = json.loads(
                (config / "plugins" / "installed_plugins.json").read_text()
            )
            self.assertEqual(
                installed["plugins"][PLUGIN_ID][0]["gitCommitSha"],
                UPSTREAM_SHA,
            )
            memory = (config / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("docs/agents/session-prompt.md", memory)
            self.assertIn("supervised", memory)
            self.assertIn("loop/run_session.sh", memory)

    def test_unexpected_marketplace_removal_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = self.make_fake_claude(root)
            setup = self.make_setup_copy(root)
            test_root = root / "alpha-lab-dev"
            env = {
                **os.environ,
                "CLAUDE_BIN": str(fake),
                "CLAUDE_CONFIG_DIR": str(test_root / "claude-config"),
                "FAKE_CLAUDE_LOG": str(root / "claude.log"),
                "FAKE_REMOVE_ERROR": "1",
            }
            result = subprocess.run(
                ["bash", str(setup)],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("temporary backend failure", result.stderr)

    def test_nested_marketplace_symlink_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = self.make_fake_claude(root)
            setup = self.make_setup_copy(root)
            test_root = root / "alpha-lab-dev"
            marketplace = test_root / "marketplace"
            outside = root / "outside"
            marketplace.mkdir(parents=True)
            outside.mkdir()
            (marketplace / ".claude-plugin").symlink_to(
                outside,
                target_is_directory=True,
            )
            env = {
                **os.environ,
                "CLAUDE_BIN": str(fake),
                "CLAUDE_CONFIG_DIR": str(test_root / "claude-config"),
                "FAKE_CLAUDE_LOG": str(root / "claude.log"),
            }
            result = subprocess.run(
                ["bash", str(setup)],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlinked setup path", result.stderr)
            self.assertFalse((outside / "marketplace.json").exists())

    def test_marketplace_manifest_symlink_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = self.make_fake_claude(root)
            setup = self.make_setup_copy(root)
            test_root = root / "alpha-lab-dev"
            plugin_dir = test_root / "marketplace" / ".claude-plugin"
            outside = root / "outside.json"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "marketplace.json").symlink_to(outside)
            env = {
                **os.environ,
                "CLAUDE_BIN": str(fake),
                "CLAUDE_CONFIG_DIR": str(test_root / "claude-config"),
                "FAKE_CLAUDE_LOG": str(root / "claude.log"),
            }
            result = subprocess.run(
                ["bash", str(setup)],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlinked setup path", result.stderr)
            self.assertFalse(outside.exists())

    def test_user_memory_symlink_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = self.make_fake_claude(root)
            setup = self.make_setup_copy(root)
            test_root = root / "alpha-lab-dev"
            config = test_root / "claude-config"
            outside = root / "outside-CLAUDE.md"
            config.mkdir(parents=True)
            outside.write_text("keep me", encoding="utf-8")
            (config / "CLAUDE.md").symlink_to(outside)
            env = {
                **os.environ,
                "CLAUDE_BIN": str(fake),
                "CLAUDE_CONFIG_DIR": str(config),
                "FAKE_CLAUDE_LOG": str(root / "claude.log"),
            }
            result = subprocess.run(
                ["bash", str(setup)],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlinked setup path", result.stderr)
            self.assertEqual(outside.read_text(encoding="utf-8"), "keep me")

    def test_missing_install_paths_fail_sha_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = self.make_fake_claude(root)
            setup = self.make_setup_copy(root)
            test_root = root / "alpha-lab-dev"
            env = {
                **os.environ,
                "CLAUDE_BIN": str(fake),
                "CLAUDE_CONFIG_DIR": str(test_root / "claude-config"),
                "FAKE_CLAUDE_LOG": str(root / "claude.log"),
                "FAKE_MISSING_PATHS": "1",
            }
            result = subprocess.run(
                ["bash", str(setup)],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA mismatch", result.stderr)

    def test_symlinked_install_path_fails_sha_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = self.make_fake_claude(root)
            setup = self.make_setup_copy(root)
            test_root = root / "alpha-lab-dev"
            env = {
                **os.environ,
                "CLAUDE_BIN": str(fake),
                "CLAUDE_CONFIG_DIR": str(test_root / "claude-config"),
                "FAKE_CLAUDE_LOG": str(root / "claude.log"),
                "FAKE_PATH_MODE": "leaf-symlink",
            }
            result = subprocess.run(
                ["bash", str(setup)],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA mismatch", result.stderr)

    def test_ancestor_symlink_and_outside_install_paths_fail(self):
        for mode in ("ancestor-symlink", "outside-root"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                fake = self.make_fake_claude(root)
                setup = self.make_setup_copy(root)
                test_root = root / "alpha-lab-dev"
                env = {
                    **os.environ,
                    "CLAUDE_BIN": str(fake),
                    "CLAUDE_CONFIG_DIR": str(test_root / "claude-config"),
                    "FAKE_CLAUDE_LOG": str(root / "claude.log"),
                    "FAKE_PATH_MODE": mode,
                }
                result = subprocess.run(
                    ["bash", str(setup)],
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=30,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("SHA mismatch", result.stderr)

    def test_script_embeds_the_reviewed_source(self):
        text = SETUP.read_text(encoding="utf-8")
        self.assertIn("https://github.com/mattpocock/skills.git", text)
        self.assertIn(UPSTREAM_SHA, text)
        self.assertIn(PLUGIN_ID, text)
        self.assertNotIn("chmod -R a+rwX", text)
        self.assertNotIn("ALPHA_LAB_SETUP_TESTING", text)

    def test_verified_receipt_is_complete_when_present(self):
        receipt = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        if receipt.get("status") == "pending":
            self.skipTest("cloud environment acceptance is pending")
        self.assertEqual(receipt.get("status"), "verified")
        self.assertEqual(receipt.get("pluginId"), PLUGIN_ID)
        self.assertEqual(receipt.get("gitCommitSha"), UPSTREAM_SHA)
        self.assertIs(receipt.get("firstSessionDirectInvocation"), True)
        self.assertIs(receipt.get("firstSessionSubagentInvocation"), True)
        self.assertIs(receipt.get("firstSessionConfigPointerLoaded"), True)
        self.assertIs(receipt.get("cachedSessionDirectInvocation"), True)
        self.assertIs(receipt.get("cachedSessionConfigPointerLoaded"), True)
        self.assertNotEqual(
            receipt.get("firstSessionUrl"),
            receipt.get("cachedSessionUrl"),
        )


if __name__ == "__main__":
    unittest.main()
