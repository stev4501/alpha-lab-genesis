"""Contract tests for developer-only skill plugins.

These plugins exist for supervised development sessions. The invariant under
test is that they stay invisible to the autonomous sessions launched by
loop/run_session.sh. See docs/dev-only-skills.md.
"""

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEV_PLUGINS = ROOT / "dev" / "plugins"
CLAUDE_DIR = ROOT / ".claude"
AGENT_SETTINGS = ROOT / "loop" / "agent-settings.json"
CLOUD_ACCEPTANCE = CLAUDE_DIR / "cloud-plugin-acceptance.json"
MARKETPLACE_NAME = "alpha-lab-pinned"
PLUGIN_NAME = "mattpocock-skills"
PLUGIN_ID = f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"
UPSTREAM_URL = "https://github.com/mattpocock/skills.git"
UPSTREAM_SHA = "84fdeffd12f2ee307994d1eb6feb48173b6e0502"
VENDORED_TREE_SHA256 = "9776f7fd3385785b812aa84fec16f49e975d9c5bf97e79c0347d2e66e0dc903f"
VERIFIED_CLAUDE_VERSION = "2.1.226"


def runner_code():
    """loop/run_session.sh with comment lines stripped.

    Assertions about what the runner does must read the code, not the prose
    around it. A comment explaining that no --plugin-dir is passed would
    otherwise fail a naive substring check, and — worse — a comment mentioning
    --disallowedTools would satisfy one.
    """
    text = (ROOT / "loop" / "run_session.sh").read_text(encoding="utf-8")
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def plugin_dirs():
    if not DEV_PLUGINS.is_dir():
        return []
    return sorted(p for p in DEV_PLUGINS.iterdir() if (p / ".claude-plugin" / "plugin.json").is_file())


class TestVendoredPluginStructure(unittest.TestCase):
    """Each vendored plugin is well formed and self-consistent."""

    def test_at_least_one_plugin_is_vendored(self):
        self.assertTrue(plugin_dirs(), "no vendored plugins found under dev/plugins/")

    def test_declared_skills_exist_and_are_named(self):
        for plugin in plugin_dirs():
            manifest = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
            declared = manifest.get("skills", [])
            self.assertTrue(declared, f"{plugin.name}: plugin.json declares no skills")
            for rel in declared:
                skill_md = plugin / rel.lstrip("./") / "SKILL.md"
                with self.subTest(plugin=plugin.name, skill=rel):
                    self.assertTrue(skill_md.is_file(), f"declared skill has no SKILL.md: {rel}")
                    text = skill_md.read_text(encoding="utf-8")
                    self.assertTrue(
                        text.startswith("---"),
                        f"{rel}/SKILL.md has no YAML frontmatter",
                    )
                    self.assertIn("name:", text.split("---")[1], f"{rel}/SKILL.md frontmatter has no name")

    def test_no_undeclared_skills_are_vendored(self):
        """Everything on disk is accounted for in plugin.json, so review covers it all."""
        for plugin in plugin_dirs():
            manifest = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
            declared = {(plugin / rel.lstrip("./")).resolve() for rel in manifest.get("skills", [])}
            found = {p.parent.resolve() for p in plugin.rglob("SKILL.md")}
            self.assertEqual(
                found - declared,
                set(),
                f"{plugin.name}: SKILL.md files on disk that plugin.json does not declare",
            )

    def test_provenance_is_recorded(self):
        for plugin in plugin_dirs():
            vendor = plugin / "VENDOR.md"
            with self.subTest(plugin=plugin.name):
                self.assertTrue(vendor.is_file(), f"{plugin.name}: no VENDOR.md")
                text = vendor.read_text(encoding="utf-8")
                self.assertIn("https://github.com/", text, "VENDOR.md records no upstream URL")
                self.assertIn("Commit", text, "VENDOR.md records no upstream commit")

    def test_vendored_tree_matches_the_reviewed_snapshot(self):
        """Every upstream-copied byte is covered by one deterministic digest."""
        plugin = DEV_PLUGINS / PLUGIN_NAME
        manifest = json.loads(
            (plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        files = [plugin / ".claude-plugin" / "plugin.json", plugin / "LICENSE"]
        for rel in manifest["skills"]:
            files.extend(sorted((plugin / rel.lstrip("./")).rglob("*")))

        digest = hashlib.sha256()
        for path in sorted({p for p in files if p.is_file()}):
            digest.update(str(path.relative_to(plugin)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())

        self.assertEqual(digest.hexdigest(), VENDORED_TREE_SHA256)
        self.assertIn(
            UPSTREAM_SHA,
            (plugin / "VENDOR.md").read_text(encoding="utf-8"),
        )


class TestDevPluginsStayOutOfAutonomousSessions(unittest.TestCase):
    """The invariant that makes these skills developer-only."""

    def test_dev_plugins_are_not_in_a_discovery_path(self):
        """dev/plugins/ must contain no .claude/skills/ tree.

        A nested .claude/skills/ directory loads automatically as soon as Claude
        reads or edits a file beneath it, which would defeat the arrangement.
        """
        if not DEV_PLUGINS.is_dir():
            self.skipTest("no dev/plugins/ directory")
        offenders = [p for p in DEV_PLUGINS.rglob(".claude") if p.is_dir()]
        self.assertEqual(offenders, [], f"nested .claude/ directories under dev/plugins/: {offenders}")

    def test_project_skills_directory_does_not_exist(self):
        """.claude/skills/ loads into every session, autonomous ones included."""
        self.assertFalse(
            (CLAUDE_DIR / "skills").exists(),
            ".claude/skills/ exists: skills placed there load into autonomous sessions too",
        )

    def test_cloud_plugin_is_declared_from_a_pinned_inline_marketplace(self):
        """Cloud delivery must resolve the reviewed upstream commit without local state."""
        settings = json.loads((CLAUDE_DIR / "settings.json").read_text(encoding="utf-8"))
        self.assertIs(settings.get("enabledPlugins", {}).get(PLUGIN_ID), True)

        marketplace = settings.get("extraKnownMarketplaces", {}).get(MARKETPLACE_NAME)
        self.assertIsNotNone(marketplace, f"{MARKETPLACE_NAME} marketplace is not declared")
        self.assertIs(marketplace.get("autoUpdate"), False)

        source = marketplace.get("source", {})
        self.assertEqual(source.get("source"), "settings")
        self.assertEqual(source.get("name"), MARKETPLACE_NAME)
        plugins = source.get("plugins")
        self.assertEqual(len(plugins or []), 1)
        self.assertEqual(plugins[0].get("name"), PLUGIN_NAME)
        self.assertEqual(
            plugins[0].get("source"),
            {
                "source": "url",
                "url": UPSTREAM_URL,
                "sha": UPSTREAM_SHA,
            },
        )

    def test_declared_cloud_plugin_requires_the_runner_controls(self):
        """The runner must remove the Skill surface whenever cloud delivery is enabled."""
        runner = runner_code()
        self.assertIn(
            "--disable-slash-commands", runner,
            f"project settings declare {PLUGIN_ID} but the runner does not disable skills",
        )
        self.assertRegex(
            runner, r'--disallowedTools\s+"Skill"',
            f"project settings declare {PLUGIN_ID} but the runner does not remove the Skill tool",
        )

    def test_autonomous_settings_disable_the_cloud_plugin(self):
        """The runner's explicit settings file must override project enablement."""
        settings = json.loads(AGENT_SETTINGS.read_text(encoding="utf-8"))
        self.assertIs(
            settings.get("enabledPlugins", {}).get(PLUGIN_ID),
            False,
            f"{PLUGIN_ID} is not explicitly disabled for autonomous sessions",
        )

    def test_runner_supplies_no_plugin_delivery_flags(self):
        """The autonomous path may disable plugins, but must never sideload one."""
        runner = runner_code()
        for flag in ("--plugin-dir", "--plugin-url"):
            self.assertNotIn(flag, runner, f"autonomous runner supplies {flag}")

    def test_autonomous_workflow_pins_the_verified_claude_version(self):
        workflow = (ROOT / ".github" / "workflows" / "session.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            f"@anthropic-ai/claude-code@{VERIFIED_CLAUDE_VERSION}",
            workflow,
        )

    def test_fresh_cloud_delivery_is_accepted_before_merge(self):
        """Validate complete evidence when present without breaking the autonomous loop."""
        acceptance = json.loads(CLOUD_ACCEPTANCE.read_text(encoding="utf-8"))
        if acceptance.get("status") == "pending":
            self.skipTest("fresh cloud acceptance is pending; PR-only check remains red")
        self.assertEqual(acceptance.get("status"), "verified")
        self.assertEqual(acceptance.get("pluginId"), PLUGIN_ID)
        self.assertEqual(acceptance.get("gitCommitSha"), UPSTREAM_SHA)
        self.assertEqual(acceptance.get("claudeVersion"), VERIFIED_CLAUDE_VERSION)
        self.assertIs(acceptance.get("directSkillInvocation"), True)
        self.assertIs(acceptance.get("subagentSkillInvocation"), True)
        self.assertTrue(acceptance.get("cloudEnvironment"))
        self.assertTrue(acceptance.get("sessionUrl"))
        self.assertTrue(acceptance.get("verifiedAt"))

class TestVendoredPluginsGrantNoTools(unittest.TestCase):
    """A plugin can ship more than skill text. Vendored ones here do not."""

    def test_no_plugin_root_components_beyond_skills(self):
        """Claude plugin components must not appear at their root discovery paths."""
        for plugin in plugin_dirs():
            for name in (
                "agents",
                "commands",
                "hooks",
                "monitors",
                "output-styles",
                ".mcp.json",
                "mcp.json",
                ".lsp.json",
                "settings.json",
            ):
                with self.subTest(plugin=plugin.name, component=name):
                    self.assertFalse(
                        (plugin / name).exists(),
                        f"{plugin.name} ships {name}; review before allowing it",
                    )

    def test_no_skill_declares_allowed_tools(self):
        """allowed-tools grants a skill unprompted tool access when invoked."""
        for plugin in plugin_dirs():
            for skill_md in sorted(plugin.rglob("SKILL.md")):
                frontmatter = skill_md.read_text(encoding="utf-8").split("---")
                if len(frontmatter) < 3:
                    continue
                with self.subTest(skill=skill_md.relative_to(ROOT)):
                    self.assertNotIn(
                        "allowed-tools",
                        frontmatter[1],
                        "vendored skill grants itself tool access; review before allowing it",
                    )

    def test_no_executable_files(self):
        for plugin in plugin_dirs():
            executables = [p for p in plugin.rglob("*") if p.is_file() and p.stat().st_mode & 0o111]
            self.assertEqual(
                executables,
                [],
                f"{plugin.name} ships executable files: {[str(p.relative_to(ROOT)) for p in executables]}",
            )


if __name__ == "__main__":
    unittest.main()
