"""Contract tests for developer-only skill plugins.

These plugins exist for supervised development sessions. The invariant under
test is that they stay invisible to the autonomous sessions launched by
loop/run_session.sh. See docs/dev-only-skills.md.
"""

import json
import os
import subprocess
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

    def test_settings_do_not_enable_dev_plugins_globally(self):
        """enabledPlugins in project settings would load these for every session."""
        settings_path = CLAUDE_DIR / "settings.json"
        if not settings_path.is_file():
            self.skipTest("no .claude/settings.json")
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertNotIn(
            "enabledPlugins",
            settings,
            "enabledPlugins in .claude/settings.json loads plugins for autonomous sessions too; "
            "load developer plugins with bin/dev-session instead",
        )

    def test_runner_loads_no_plugins(self):
        """loop/run_session.sh must never pass a plugin flag."""
        runner = runner_code()
        for flag in ("--plugin-dir", "--plugin-url"):
            self.assertNotIn(flag, runner, f"loop/run_session.sh passes {flag}")

    def test_runner_disables_skills(self):
        """The autonomous session must not be able to run a skill at all.

        Two independent controls, either of which suffices: the feature-level
        --disable-slash-commands, and a bare "Skill" in --disallowedTools, which
        drops the tool from the agent's context. Both are asserted so that
        removing one is a deliberate edit to this test rather than a silent
        weakening.
        """
        runner = runner_code()
        self.assertIn("--disable-slash-commands", runner)
        self.assertRegex(runner, r'--disallowedTools\s+"Skill"')

    def test_runner_denies_reading_vendored_plugins(self):
        """Vendored skills are not loaded here; keep them out of context as prose too."""
        runner = runner_code()
        self.assertIn('"Read(dev/plugins/**)"', runner)

    def _run_wrapper(self, *args, claude_bin="/bin/false"):
        """Run bin/dev-session with a stubbed CLAUDE_BIN.

        The stub matters. If the -p guard below were ever removed, an unstubbed
        run would exec the real CLI and start an agent session inside the test
        suite — spending money and hanging CI on a test whose whole point is
        that the wrapper refuses. With the stub the worst case is a wrong exit
        code, which fails fast. The timeout is a second backstop.
        """
        env = {**os.environ, "CLAUDE_BIN": claude_bin}
        return subprocess.run(
            [str(ROOT / "bin" / "dev-session"), *args],
            capture_output=True, text=True, cwd=ROOT, env=env, timeout=30,
        )

    def test_dev_session_refuses_non_interactive(self):
        """bin/dev-session must not be usable to get skills into a headless run.

        Print mode is not the only way to reach an unattended session, so this
        covers the class. Two forms are easy to miss and both were live holes:
        clustered short flags (`-pd`, `-dp` engage --print exactly as `-p`
        does, so an exact-match guard misses every cluster), and the background
        agent flags (`--bg`/`--background`, documented as starting a background
        agent, which runs locally with the plugin loaded). `--cloud` is refused
        on precaution. `--print=true` is currently rejected by the CLI itself
        and is covered here so the wrapper does not depend on that.
        """
        self.assertTrue((ROOT / "bin" / "dev-session").is_file(), "bin/dev-session missing")
        for flag in ("-p", "--print", "--print=true", "-pd", "-dp", "-pv",
                     "--bg", "--background", "--cloud", "--cloud=desc",
                     "--remote", "--remote=task"):
            result = self._run_wrapper(flag, "noop")
            with self.subTest(flag=flag):
                self.assertEqual(result.returncode, 2, f"{flag} was not refused")
                self.assertIn("refusing non-interactive mode", result.stderr)

    def test_dev_session_honours_end_of_options(self):
        """`--` ends option scanning; what follows is positional text.

        Without this the wrapper refuses `dev-session -- --bg`, where --bg is a
        prompt the developer wants to talk about rather than a flag. The second
        case guards the obvious wrong fix: a flag BEFORE the marker must still
        be caught.
        """
        allowed = self._run_wrapper("--", "--bg", claude_bin="/bin/true")
        self.assertEqual(
            allowed.returncode, 0,
            f"positional text after -- was refused: {allowed.stderr}",
        )
        refused = self._run_wrapper("--bg", "--", "x")
        self.assertEqual(
            refused.returncode, 2,
            "a flag before -- must still be refused",
        )

    def test_dev_session_still_accepts_interactive_use(self):
        """The guard must reject -p, not everything.

        Without this, a guard that refused every invocation would pass the test
        above and quietly break the only supported way to use these skills.
        /bin/true stands in for the CLI and ignores its arguments, so reaching
        it at all is the signal.
        """
        for args in (
            ("--model", "sonnet"),
            ("--permission-mode", "plan"),   # long flag starting with p
            ("-d",),                         # short flag without p
            ("-c",),
            ("--remote-control",),           # documented as interactive
            ("--rc",),                       # its alias, likewise
            ("-w",),
            ("explain --bg and -p",),        # positional mentioning flags
        ):
            result = self._run_wrapper(*args, claude_bin="/bin/true")
            with self.subTest(args=args):
                self.assertEqual(
                    result.returncode, 0,
                    f"ordinary invocation {args} was refused: {result.stderr}",
                )
                self.assertNotIn("refusing non-interactive mode", result.stderr)


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
