"""Contract tests for where the agent deny rules live and what they cover.

BL-0006 recorded the asymmetry these tests now pin down: `.claude/settings.json`
binds every Claude Code session opened in this repository, but the rules in it
were written for the unattended agent `loop/run_session.sh` launches. The
operator resolved it on 2026-08-09 (BL-0006 option 3):

- **Repo-wide, every session:** evidence immutability (`results/`, `reviews/`,
  `data/snapshots|raw|provenance/`) and the `main`/history guardrails.
- **Runner-only, the unattended agent:** everything that makes the core
  human-owned — the sealed components, the loop machinery, the protected root
  files — plus the network and install denies, in `loop/agent-settings.json`,
  passed with `--settings`.

The invariant worth defending is not "these exact rules exist". It is that
moving them did not create a gap: the runner is never less constrained than the
repository default, it covers every path the validator would fail a session for
touching, and it refuses to start when it cannot load them.
"""

import fcntl
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "loop" / "run_session.sh"
VALIDATOR = ROOT / "loop" / "validate_session.sh"
AGENT_SETTINGS = ROOT / "loop" / "agent-settings.json"
REPO_SETTINGS = ROOT / ".claude" / "settings.json"

#: Paths whose ownership moved to the runner. Supervised sessions may edit
#: these; the unattended agent may not. Kept explicit so a silent re-add to
#: `.claude/settings.json` fails a test instead of quietly restoring the
#: friction BL-0006 exists to remove.
CORE_PATHS = (
    "evaluator/**",
    "scripts/**",
    "schemas/**",
    "loop/**",
    ".github/**",
    ".claude/**",
    "CORE_MANIFEST.json",
    "MISSION.md",
    "CONTEXT.md",
    "CODEOWNERS",
)

#: Paths that stay denied for every session regardless of supervision. Recorded
#: evidence is immutable to any automated writer; a human who needs to correct
#: it does so by hand, deliberately, outside an agent session.
EVIDENCE_PATHS = (
    "results/**",
    "reviews/**",
    "data/snapshots/**",
    "data/raw/**",
    "data/provenance/**",
)


def runner_code():
    """`loop/run_session.sh` with comment lines stripped.

    Same reasoning as `tests/test_dev_plugins.py`: assertions about what the
    runner does must read the code, not the prose around it. The comments in
    this file mention `--settings` several times.
    """
    text = RUNNER.read_text(encoding="utf-8")
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def deny_rules(path: Path) -> set:
    return set(json.loads(path.read_text(encoding="utf-8"))["permissions"]["deny"])


def validator_protected_paths() -> list:
    """The path prefixes in check 1 of `loop/validate_session.sh`.

    Read out of the validator rather than restated, so that a path added to the
    gate and not to the deny rules shows up here as a failure rather than as a
    session that burns ninety minutes and then fails validation.
    """
    text = VALIDATOR.read_text(encoding="utf-8")
    match = re.search(r"^PROTECTED='(.+)'$", text, re.MULTILINE)
    assert match, "could not find the PROTECTED regex in loop/validate_session.sh"
    body = match.group(1).removeprefix("^(").removesuffix(")")
    paths = []
    for alternative in body.split("|"):
        bare = alternative.removesuffix("$").replace("\\", "")
        paths.append(f"{bare}**" if bare.endswith("/") else bare)
    return paths


class TestSettingsSplit(unittest.TestCase):
    """Which file carries which rule."""

    def test_repository_default_keeps_evidence_immutable(self):
        rules = deny_rules(REPO_SETTINGS)
        for path in EVIDENCE_PATHS:
            for tool in ("Edit", "Write"):
                with self.subTest(rule=f"{tool}({path})"):
                    self.assertIn(
                        f"{tool}({path})", rules,
                        "recorded evidence must stay denied to every session, "
                        "supervised or not",
                    )

    def test_repository_default_does_not_own_the_core(self):
        """The change itself: supervised sessions can repair the loop.

        A supervised session is governed by the human in it. Re-adding these to
        `.claude/settings.json` would restore the state BL-0006 describes, where
        the supervised path for repairing the loop is strictly more awkward than
        the unsupervised path for running it.
        """
        rules = deny_rules(REPO_SETTINGS)
        for path in CORE_PATHS:
            for tool in ("Edit", "Write"):
                with self.subTest(rule=f"{tool}({path})"):
                    self.assertNotIn(
                        f"{tool}({path})", rules,
                        "core ownership belongs in loop/agent-settings.json; in "
                        "the repository default it also binds supervised sessions",
                    )

    def test_runner_settings_own_the_core(self):
        rules = deny_rules(AGENT_SETTINGS)
        for path in CORE_PATHS:
            for tool in ("Edit", "Write"):
                with self.subTest(rule=f"{tool}({path})"):
                    self.assertIn(f"{tool}({path})", rules)

    def test_runner_is_never_less_constrained_than_the_default(self):
        """`loop/agent-settings.json` is a superset, deliberately.

        Deny rules from every settings source are unioned, so the unattended
        agent would inherit the repository default anyway — this file does not
        need to restate it. It restates it so that trimming `.claude/settings.json`
        in some later session cannot silently loosen the unattended path, which
        is the one nobody is watching.
        """
        missing = deny_rules(REPO_SETTINGS) - deny_rules(AGENT_SETTINGS)
        self.assertEqual(
            set(), missing,
            f"repo-wide rules absent from the runner's settings: {sorted(missing)}",
        )

    def test_runner_settings_cover_every_validator_protected_path(self):
        """No path fails the gate without also failing at the point of attempt."""
        rules = deny_rules(AGENT_SETTINGS)
        for path in validator_protected_paths():
            for tool in ("Edit", "Write"):
                with self.subTest(rule=f"{tool}({path})"):
                    self.assertIn(
                        f"{tool}({path})", rules,
                        f"{path} fails loop/validate_session.sh but is writable "
                        "during the session",
                    )


class TestRunnerLoadsTheSettings(unittest.TestCase):
    """The flag is passed, and its absence is fatal rather than silent."""

    def test_runner_passes_the_settings_file(self):
        code = runner_code()
        self.assertRegex(code, r'AGENT_SETTINGS="loop/agent-settings\.json"')
        self.assertRegex(code, r'--settings\s+"\$AGENT_SETTINGS"')

    def test_settings_file_is_valid_json(self):
        json.loads(AGENT_SETTINGS.read_text(encoding="utf-8"))


class TestRunnerFailsClosedOnMissingSettings(unittest.TestCase):
    """Behavioural: run the real preflight against a scratch repository.

    A repo-wide default cannot be forgotten; an explicitly passed file can. The
    preflight is what converts that trade from a silent loss of constraint into
    a refusal, so it is tested by running it rather than by reading it.
    """

    def _scratch_repo(self, settings: str | None):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        run = lambda *a: subprocess.run(a, cwd=tmp, check=True, capture_output=True)
        run("git", "init", "-q", "-b", "main")
        run("git", "config", "user.email", "test@example.invalid")
        run("git", "config", "user.name", "test")
        (tmp / "loop").mkdir()
        shutil.copy(RUNNER, tmp / "loop" / "run_session.sh")
        if settings is not None:
            (tmp / "loop" / "agent-settings.json").write_text(settings, encoding="utf-8")
        run("git", "add", "-A")
        run("git", "commit", "-q", "-m", "scratch")
        return tmp

    def _run_preflight(self, settings: str | None):
        """Run the real runner against a scratch repository.

        `LOCKFILE` is per-scratch-repo on purpose. `run_session.sh` runs the
        test suite from inside its own `flock` region, so a test that launched a
        runner on the default lock path would collide with the session running
        it: the child sees "another session is running", exits 0, and never
        reaches the preflight under test. That failure only appears when the
        suite runs the way the loop actually runs it, which is the way that
        matters — a green local suite would have put every autonomous run into
        maintenance mode.
        """
        tmp = self._scratch_repo(settings)
        # Outside the repository, not in it: the runner creates the lock file
        # before it checks for a clean working tree, so a lock inside the tree
        # trips the preceding preflight instead.
        lock = tmp.with_suffix(".lock")
        self.addCleanup(lock.unlink, True)
        return subprocess.run(
            ["bash", "loop/run_session.sh"],
            cwd=tmp, capture_output=True, text=True,
            env={
                "PATH": os.environ["PATH"],
                "REPO_DIR": str(tmp),
                "LOCKFILE": str(lock),
            },
        )

    def test_missing_settings_file_stops_the_session(self):
        result = self._run_preflight(None)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("refusing to run an unconstrained session", result.stdout)
        self.assertIn("is missing", result.stdout)

    def test_malformed_settings_file_stops_the_session(self):
        result = self._run_preflight('{"permissions": {"deny": [')
        self.assertNotEqual(0, result.returncode)
        self.assertIn("refusing to run an unconstrained session", result.stdout)
        self.assertIn("not valid JSON", result.stdout)

    def test_valid_settings_file_clears_the_preflight(self):
        """Positive control: the run still fails, but never at this check.

        The scratch repository has no validator, no prompts, and no agent, so
        the run dies shortly after. What matters is which failure it is — a test
        asserting only "nonzero" above would pass even if the preflight rejected
        every input.
        """
        result = self._run_preflight('{"permissions": {"deny": []}}')
        self.assertNotIn("refusing to run an unconstrained session", result.stdout)

    def test_preflight_is_reachable_while_a_session_holds_the_default_lock(self):
        """The regression guard for the collision described in `_run_preflight`.

        Equivalent to the reviewer's reproduction, `flock
        /tmp/alpha-lab-session.lock python -m unittest ...`, but self-contained:
        hold the default lock, then check the scratch runner still gets past the
        lock guard to the check under test. If `LOCKFILE` ever stops being
        env-overridable, this fails with the exit-0 "another session" path.
        """
        default_lock = open("/tmp/alpha-lab-session.lock", "w")
        self.addCleanup(default_lock.close)
        try:
            fcntl.flock(default_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.skipTest("a real session holds /tmp/alpha-lab-session.lock")
        result = self._run_preflight(None)
        self.assertNotIn("Another session is running", result.stdout + result.stderr)
        self.assertIn("refusing to run an unconstrained session", result.stdout)


if __name__ == "__main__":
    unittest.main()
