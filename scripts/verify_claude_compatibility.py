#!/usr/bin/env python3
"""Verify the Claude CLI behaviours that bin/dev-session depends on."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Callable, Protocol, Sequence


PLUGIN_PATH = Path("dev/plugins/mattpocock-skills")
COMMAND_TIMEOUT_SECONDS = 30.0
DISCOVERY_POLLS = 10
CLEANUP_POLLS = 30
REQUIRED_EMPTY_POLLS = 10
POLL_INTERVAL_SECONDS = 0.5
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{4,}")
VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
LAUNCH_PATTERN = re.compile(r"^backgrounded · ([A-Za-z0-9_-]{4,})$")


@dataclass(frozen=True)
class CommandResult:
    arguments: tuple[str, ...]
    cwd: Path
    returncode: int
    output: str


class ClaudeCli(Protocol):
    binary: Path

    def execute(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
    ) -> CommandResult: ...


@dataclass(frozen=True)
class VerificationReport:
    outcome: str
    verified_at: str
    binary: Path
    version: str | None
    commands: tuple[CommandResult, ...]
    failures: tuple[str, ...]
    observations: tuple[str, ...]
    launcher_ids: tuple[str, ...]
    owned_session_ids: tuple[str, ...]
    cleanup_verified: bool

    @property
    def exit_code(self) -> int:
        if self.outcome == "confirmed":
            return 0
        if self.outcome == "interrupted":
            return 130
        return 1


class SubprocessClaudeCli:
    def __init__(self, binary: Path):
        resolved = binary.resolve()
        if not resolved.is_file() or not resolved.stat().st_mode & 0o111:
            raise ValueError(f"Claude binary is not executable: {resolved}")
        self.binary = resolved

    @classmethod
    def from_path(cls) -> "SubprocessClaudeCli":
        found = shutil.which("claude")
        if found is None:
            raise ValueError("claude is not on PATH")
        return cls(Path(found))

    def execute(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
    ) -> CommandResult:
        argv = (str(self.binary), *arguments)
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"Could not execute {argv!r}: {exc}") from exc
        return CommandResult(
            tuple(arguments),
            cwd,
            completed.returncode,
            completed.stdout,
        )


@dataclass(frozen=True)
class _ActiveSession:
    session_id: str
    cwd: Path


class _AmbiguousSessionIdentity(ValueError):
    def __init__(self, session_id: str):
        super().__init__(
            f"agents --json has duplicate active-session id {session_id}"
        )
        self.session_id = session_id


def _parse_active_sessions(output: str) -> tuple[_ActiveSession, ...]:
    try:
        records = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ValueError(f"agents --json returned invalid JSON: {exc}") from exc
    if not isinstance(records, list):
        raise ValueError("agents --json top level is not a list")
    sessions = []
    seen_ids = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"agents --json item {index} is not an object")
        session_id = record.get("id")
        cwd = record.get("cwd")
        if not isinstance(session_id, str) or ID_PATTERN.fullmatch(session_id) is None:
            raise ValueError(f"agents --json item {index} has no valid id")
        if not isinstance(cwd, str) or not Path(cwd).is_absolute():
            raise ValueError(f"agents --json item {index} has no absolute cwd")
        if session_id in seen_ids:
            raise _AmbiguousSessionIdentity(session_id)
        seen_ids.add(session_id)
        sessions.append(_ActiveSession(session_id, Path(cwd).resolve()))
    return tuple(sessions)


def _launcher_ids(output: str) -> tuple[str, ...]:
    return tuple(
        match.group(1)
        for line in output.splitlines()
        if (match := LAUNCH_PATTERN.fullmatch(line)) is not None
    )


def verify(
    claude: ClaudeCli,
    repository: Path,
    *,
    sleep: Callable[[float], None] = time.sleep,
    temp_parent: Path | None = None,
) -> VerificationReport:
    """Run both compatibility probes and converge cleanup before returning."""

    repository = repository.resolve()
    plugin = repository / PLUGIN_PATH
    plugin_manifest = plugin / ".claude-plugin" / "plugin.json"
    if not plugin_manifest.is_file():
        raise ValueError(f"Plugin manifest is missing: {plugin_manifest}")

    commands: list[CommandResult] = []
    failures: list[str] = []
    observations: list[str] = []
    launchers: list[str] = []
    owned_ids: list[str] = []
    unsafe_launcher_ids: set[str] = set()
    version: str | None = None
    cleanup_verified = False
    outcome = "confirmed"
    interrupted = False

    def execute(arguments: Sequence[str], *, cwd: Path) -> CommandResult:
        try:
            result = claude.execute(
                tuple(arguments),
                cwd=cwd,
                timeout_seconds=COMMAND_TIMEOUT_SECONDS,
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            raise RuntimeError(
                f"Claude command {tuple(arguments)!r} could not run: {exc}"
            ) from exc
        commands.append(result)
        return result

    def active_sessions() -> tuple[_ActiveSession, ...]:
        result = execute(("agents", "--json"), cwd=repository)
        if result.returncode != 0:
            raise RuntimeError(f"agents --json exited {result.returncode}")
        return _parse_active_sessions(result.output)

    def fail(kind: str, message: str) -> None:
        nonlocal outcome
        failures.append(message)
        if kind == "unverified" or outcome == "confirmed":
            outcome = kind

    try:
        version_result = execute(("--version",), cwd=repository)
    except Exception as exc:
        fail("unverified", f"Version lookup could not run: {exc}")
        return _report(
            claude,
            version,
            commands,
            failures,
            observations,
            launchers,
            owned_ids,
            cleanup_verified,
            outcome,
        )
    if version_result.returncode != 0:
        fail("unverified", f"Version lookup exited {version_result.returncode}.")
    else:
        first_line = version_result.output.splitlines()[0] if version_result.output else ""
        token = first_line.split(maxsplit=1)[0] if first_line else ""
        if VERSION_PATTERN.fullmatch(token) is None:
            fail("changed", f"Unexpected Claude version output: {first_line!r}.")
        else:
            version = token

    try:
        print_probe = execute(("-pd", "say ok"), cwd=repository)
    except Exception as exc:
        fail("unverified", f"Clustered-print probe could not run: {exc}")
        return _report(
            claude,
            version,
            commands,
            failures,
            observations,
            launchers,
            owned_ids,
            cleanup_verified,
            outcome,
        )
    if not (
        print_probe.returncode == 1
        and "Input must be provided" in print_probe.output
        and "--print" in print_probe.output
    ):
        fail("changed", "Clustered short flags no longer produce the --print input error.")
    else:
        observations.append("clustered short flags still engage --print")

    try:
        baseline = active_sessions()
    except (RuntimeError, ValueError) as exc:
        fail("unverified", f"Cannot establish the active-session baseline: {exc}")
        baseline = ()

    if outcome == "unverified":
        return _report(
            claude,
            version,
            commands,
            failures,
            observations,
            launchers,
            owned_ids,
            cleanup_verified,
            outcome,
        )

    baseline_ids = {session.session_id for session in baseline}
    try:
        probe_cwd = Path(
            tempfile.mkdtemp(prefix="claude-compat-", dir=temp_parent)
        ).resolve()
    except OSError as exc:
        fail("unverified", f"Could not create temporary probe directory: {exc}")
        return _report(
            claude,
            version,
            commands,
            failures,
            observations,
            launchers,
            owned_ids,
            cleanup_verified,
            outcome,
        )
    previous_signal_handlers = {}

    def note_interruption(signum, _frame) -> None:
        nonlocal interrupted
        interrupted = True
        observations.append(f"received signal {signum}; cleanup continued")

    signal_setup_error = None
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            previous_signal_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, note_interruption)
        except (OSError, ValueError) as exc:
            signal_setup_error = exc
            break
    if signal_setup_error is not None:
        restoration_errors = []
        for signum, handler in previous_signal_handlers.items():
            try:
                signal.signal(signum, handler)
            except (OSError, ValueError) as exc:
                restoration_errors.append(f"{signum}: {exc}")
        fail(
            "unverified",
            "Could not install cleanup signal handlers: "
            f"{signal_setup_error}"
            + (
                "; restoration also failed: " + ", ".join(restoration_errors)
                if restoration_errors
                else ""
            ),
        )
        try:
            shutil.rmtree(probe_cwd)
        except OSError as exc:
            failures.append(f"Could not remove unused probe directory: {exc}")
        return _report(
            claude,
            version,
            commands,
            failures,
            observations,
            launchers,
            owned_ids,
            cleanup_verified,
            outcome,
        )

    def owned(sessions: Sequence[_ActiveSession]) -> tuple[str, ...]:
        return tuple(
            session.session_id
            for session in sessions
            if session.session_id not in baseline_ids and session.cwd == probe_cwd
        )

    try:
        launch = execute(
            ("--plugin-dir", str(plugin), "--", "--bg"),
            cwd=probe_cwd,
        )
        launchers.extend(_launcher_ids(launch.output))
        if launch.returncode != 0:
            fail("changed", f"Background probe exited {launch.returncode}, expected 0.")
        if len(launchers) != 1:
            fail(
                "changed",
                f"Expected one backgrounded launcher id, found {len(launchers)}.",
            )
        colliding_launchers = set(launchers) & baseline_ids
        if colliding_launchers:
            fail(
                "unverified",
                "Launcher id collides with a pre-existing session: "
                + ", ".join(sorted(colliding_launchers)),
            )

        discovered: tuple[str, ...] = ()
        for _ in range(DISCOVERY_POLLS):
            try:
                current_sessions = active_sessions()
                for session in current_sessions:
                    if (
                        session.session_id in launchers
                        and session.cwd != probe_cwd
                    ):
                        unsafe_launcher_ids.add(session.session_id)
                discovered = owned(current_sessions)
            except _AmbiguousSessionIdentity as exc:
                if exc.session_id in launchers:
                    unsafe_launcher_ids.add(exc.session_id)
                fail("unverified", f"Cannot discover the probe session: {exc}")
                break
            except (RuntimeError, ValueError) as exc:
                fail("unverified", f"Cannot discover the probe session: {exc}")
                break
            if discovered:
                break
            sleep(POLL_INTERVAL_SECONDS)
        if unsafe_launcher_ids:
            fail(
                "unverified",
                "Launcher id is active outside the probe directory: "
                + ", ".join(sorted(unsafe_launcher_ids)),
            )
        for session_id in discovered:
            if session_id not in owned_ids:
                owned_ids.append(session_id)
        if not discovered:
            fail(
                "changed",
                "No owned active session appeared for the background probe.",
            )
        else:
            observations.append(
                f"post-marker --bg started launcher {launchers[0] if launchers else 'unknown'} "
                f"and active sessions {', '.join(discovered)}"
            )
    except KeyboardInterrupt:
        interrupted = True
        fail("interrupted", "Verification was interrupted.")
    except (RuntimeError, ValueError) as exc:
        fail("unverified", f"Background probe could not run: {exc}")
    finally:
        try:
            safe_launchers = tuple(
                session_id
                for session_id in launchers
                if session_id not in baseline_ids
                and session_id not in unsafe_launcher_ids
            )
            stop_targets = tuple(
                session_id
                for session_id in dict.fromkeys((*safe_launchers, *owned_ids))
                if session_id not in unsafe_launcher_ids
            )
            for session_id in stop_targets:
                try:
                    stop_result = execute(("stop", session_id), cwd=repository)
                    if stop_result.returncode != 0:
                        observations.append(
                            f"stop {session_id} exited {stop_result.returncode}; "
                            "absence remained authoritative"
                        )
                except Exception as exc:
                    fail("unverified", f"Stop {session_id} could not run: {exc}")

            empty_polls = 0
            for _ in range(CLEANUP_POLLS):
                try:
                    current_sessions = active_sessions()
                except Exception as exc:
                    fail("unverified", f"Cleanup is unverified: {exc}")
                    break
                for session in current_sessions:
                    if (
                        session.session_id in launchers
                        and session.cwd != probe_cwd
                    ):
                        unsafe_launcher_ids.add(session.session_id)
                active_owned = tuple(
                    session_id
                    for session_id in owned(current_sessions)
                    if session_id not in unsafe_launcher_ids
                )
                observations.append(
                    "cleanup read owned ids: "
                    + (", ".join(active_owned) if active_owned else "none")
                )
                if active_owned:
                    empty_polls = 0
                    for session_id in active_owned:
                        if session_id not in owned_ids:
                            owned_ids.append(session_id)
                        try:
                            stop_result = execute(
                                ("stop", session_id),
                                cwd=repository,
                            )
                            if stop_result.returncode != 0:
                                observations.append(
                                    f"stop {session_id} exited "
                                    f"{stop_result.returncode}; absence remained "
                                    "authoritative"
                                )
                        except Exception as exc:
                            fail(
                                "unverified",
                                f"Stop {session_id} could not run: {exc}",
                            )
                else:
                    empty_polls += 1
                    if empty_polls >= REQUIRED_EMPTY_POLLS:
                        cleanup_verified = True
                        break
                sleep(POLL_INTERVAL_SECONDS)
            if not cleanup_verified:
                fail(
                    "unverified",
                    "Cleanup did not converge to a stable empty session set.",
                )
            if unsafe_launcher_ids:
                cleanup_verified = False
                fail(
                    "unverified",
                    "Cleanup cannot own launcher ids active outside the probe "
                    "directory: "
                    + ", ".join(sorted(unsafe_launcher_ids)),
                )
            if cleanup_verified:
                try:
                    shutil.rmtree(probe_cwd)
                except OSError as exc:
                    cleanup_verified = False
                    fail(
                        "unverified",
                        f"Cleanup could not remove probe directory {probe_cwd}: {exc}",
                    )
        except Exception as exc:
            cleanup_verified = False
            fail("unverified", f"Cleanup raised unexpectedly: {exc}")
        finally:
            for signum, handler in previous_signal_handlers.items():
                signal.signal(signum, handler)

    if interrupted and cleanup_verified and outcome != "unverified":
        outcome = "interrupted"
    elif cleanup_verified and not failures:
        outcome = "confirmed"

    return _report(
        claude,
        version,
        commands,
        failures,
        observations,
        launchers,
        owned_ids,
        cleanup_verified,
        outcome,
    )


def _report(
    claude: ClaudeCli,
    version: str | None,
    commands: Sequence[CommandResult],
    failures: Sequence[str],
    observations: Sequence[str],
    launchers: Sequence[str],
    owned_ids: Sequence[str],
    cleanup_verified: bool,
    outcome: str,
) -> VerificationReport:
    return VerificationReport(
        outcome=outcome,
        verified_at=datetime.now(timezone.utc).isoformat(),
        binary=claude.binary,
        version=version,
        commands=tuple(commands),
        failures=tuple(failures),
        observations=tuple(observations),
        launcher_ids=tuple(launchers),
        owned_session_ids=tuple(owned_ids),
        cleanup_verified=cleanup_verified,
    )


def render_audit(report: VerificationReport) -> str:
    """Render one ready-to-append Markdown run-log entry."""

    lines = [
        f"**{report.verified_at} — {report.version or 'unknown'} — {report.outcome}**",
        "",
        f"- Binary: `{report.binary}`",
        f"- Cleanup verified: `{str(report.cleanup_verified).lower()}`",
        f"- Launcher ids: `{', '.join(report.launcher_ids) or 'none'}`",
        f"- Owned active-session ids: `{', '.join(report.owned_session_ids) or 'none'}`",
        "- Commands:",
    ]
    for command in report.commands:
        rendered = shlex.join(command.arguments)
        lines.append(
            f"  - `{report.binary} {rendered}` in `{command.cwd}` "
            f"→ exit `{command.returncode}`"
        )
        digest = hashlib.sha256(command.output.encode("utf-8")).hexdigest()
        lines.append(f"    - Output SHA-256: `{digest}`")
        if command.arguments != ("agents", "--json") and command.output:
            bounded_output = command.output[-500:]
            label = "Output" if len(command.output) <= 500 else "Output tail"
            lines.append(
                f"    - {label}: `{json.dumps(bounded_output, ensure_ascii=False)}`"
            )
    if report.observations:
        lines.append("- Observations:")
        lines.extend(f"  - {item}" for item in report.observations)
    if report.failures:
        lines.append("- Failures:")
        lines.extend(f"  - {item}" for item in report.failures)
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv:
        print("verify_claude_compatibility.py takes no arguments", file=sys.stderr)
        return 2
    repository = Path(__file__).resolve().parents[1]
    try:
        claude = SubprocessClaudeCli.from_path()
        report = verify(claude, repository)
    except (RuntimeError, ValueError) as exc:
        print(f"Compatibility verification could not start: {exc}", file=sys.stderr)
        return 2
    print(render_audit(report), end="")
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
