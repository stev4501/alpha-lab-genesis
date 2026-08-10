"""Contract tests for developer-only skill plugins.

These plugins exist for supervised development sessions. The invariant under
test is that they stay invisible to the autonomous sessions launched by
loop/run_session.sh. See docs/dev-only-skills.md.
"""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEV_PLUGINS = ROOT / "dev" / "plugins"
CLAUDE_DIR = ROOT / ".claude"


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

    def test_cloud_environment_is_the_only_supported_delivery_route(self):
        self.assertFalse(
            (ROOT / "bin" / "dev-session").exists(),
            "local dev-session wrapper was reintroduced without a supported caller",
        )
        documentation = (ROOT / "docs" / "dev-only-skills.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Supported route", documentation)
        self.assertIn("Alpha Lab Dev", documentation)
        self.assertNotIn("bin/dev-session", documentation)

    def test_declaring_plugins_requires_the_runner_controls(self):
        """If project settings ever declare a plugin, the runner must strip skills.

        Conditional on purpose. An earlier revision asserted a specific
        `enabledPlugins` entry unconditionally, because that declaration was
        believed to be how cloud sessions received these skills. A probe on a
        fresh cloud session disproved it (see docs/dev-only-skills.md), so the
        declaration was removed — and a test demanding a key that does nothing
        would fail the suite for anyone who sensibly deleted it.

        The invariant that survives is the safety one: a declared plugin loads
        into any session reading project settings, so declaring one is only safe
        while the runner removes skills. Nothing declared, nothing to check.
        """
        settings_path = CLAUDE_DIR / "settings.json"
        if not settings_path.is_file():
            self.skipTest("no .claude/settings.json")
        declared = json.loads(settings_path.read_text(encoding="utf-8")).get("enabledPlugins") or {}
        if not declared:
            return  # nothing declared: the invariant is vacuously satisfied
        runner = runner_code()
        self.assertIn(
            "--disable-slash-commands", runner,
            f"project settings declare plugins {list(declared)} but the runner does not disable skills",
        )
        self.assertRegex(
            runner, r'--disallowedTools\s+"Skill"',
            f"project settings declare plugins {list(declared)} but the runner does not remove the Skill tool",
        )


class TestVendoredPluginsGrantNoTools(unittest.TestCase):
    """A plugin can ship more than skill text. Vendored ones here do not."""

    def test_no_hooks_or_mcp_servers(self):
        for plugin in plugin_dirs():
            for name in ("hooks", ".mcp.json", "mcp.json"):
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
