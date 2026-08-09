"""BL-0001: golden replay of E-0002.

Re-runs the sealed EV-0002 evaluator against E-0002's exact preregistered
inputs inside a scratch repository root and asserts the deterministic outputs
are byte-identical to the recorded ones.

Nothing under `results/` is written or modified: `evaluate()` takes a `--root`,
so the replay builds a throwaway root under `tempfile` that mirrors only the
paths the evaluator reads. A guard test re-hashes every file in
`results/E-0002/` before and after the replay and fails if any byte moved.

Two inputs cannot be taken from the working tree as it stands today, both for
recorded reasons. Neither is a workaround: in both cases the evaluator's own
identity checks still run and still have to pass.

1. `DATA_MANIFEST.json` has advanced to manifest_version 1.2.0, and the
   evaluator refuses to run unless the manifest's sha256 equals the
   preregistered `design.data_manifest_sha256`. The replay therefore reads the
   1.0.0 bytes out of git at `design.code_commit` and asserts their sha256
   equals the preregistered value before using them. The manifest-hash
   difference is thus handled by pinning, not by relaxing the check.
2. That 1.0.0 manifest resolves D-0001 to `data/SPY_...csv`, a duplicate the
   2026-08-08 MVP reduction deleted after verifying byte-identity with the
   content-addressed copy under `data/snapshots/D-0001/`. The snapshot file's
   name is its own sha256 and equals the manifest's recorded checksum, so the
   replay copies those bytes to the old path inside the scratch root. The
   evaluator re-hashes the file and would reject any substitution.

`CORE_MANIFEST.json` is likewise read at `design.code_commit`, because the
evaluator requires `design.system_generation` to equal the manifest's
generation and E-0002 ran under G-0002 while the repository is now at G-0003.
The replay asserts that the sealed sha256 recorded for `evaluator/daily_bar.py`
at that commit equals the sha256 of the evaluator file being replayed, which is
what makes "same evaluator" a checked fact rather than an assumption.

`run.log` is excluded from the comparison: it embeds a wall-clock
`finished_at`, so it is non-deterministic by construction.

No network access is required. `git show` reads only local objects; the loop
runner checks out with `fetch-depth: 0`.
"""

import csv
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ID = "E-0002"
RESULT_DIR = ROOT / "results" / EXPERIMENT_ID

# Recorded in backlog/BL-0001-golden-replay-e0002.md as the baseline output.
BASELINE_METRICS_SHA256 = (
    "17ba4a0d72b1022e402adc51d35f53222e90473921cac2f3c27fcf2d9450b88e"
)

# Deterministic evaluator outputs. run.log is deliberately absent (timestamp),
# and artifact-manifest.json is absent because it hashes run.log.
DETERMINISTIC_OUTPUTS = ("validity.json", "equity.csv", "trades.csv")

# Metrics whose value depends on how the interpreter sums a list of floats.
# See test_turnover_gap_is_float_summation_semantics for the mechanism.
INTERPRETER_SENSITIVE_METRICS = ("turnover",)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_show(commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git show {commit}:{path} failed (rc={completed.returncode}). "
            "A shallow clone cannot run this replay; fetch full history. "
            f"stderr: {completed.stderr.decode('utf-8', 'replace').strip()}"
        )
    return completed.stdout


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before executing: the evaluator uses `from __future__ import
    # annotations` with @dataclass, and dataclasses resolves the string
    # annotations through sys.modules[cls.__module__].
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class GoldenReplayE0002(unittest.TestCase):
    """Replay E-0002 once for the whole class; assert on the outputs."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.prereg = json.loads((RESULT_DIR / "preregistration.json").read_text())
        cls.design = cls.prereg["design"]
        cls.commit = cls.design["code_commit"]

        # Hash the untouchable evidence before the replay runs.
        cls.evidence_before = {
            path.name: sha256_file(path)
            for path in sorted(RESULT_DIR.iterdir())
            if path.is_file()
        }

        cls._tmp = tempfile.TemporaryDirectory(prefix="golden-replay-e0002-")
        cls.scratch = Path(cls._tmp.name).resolve()
        cls.manifest_bytes = git_show(cls.commit, "DATA_MANIFEST.json")
        cls.core_bytes = git_show(cls.commit, "CORE_MANIFEST.json")
        cls._build_scratch_root()

        evaluator = load_module("replay_daily_bar", ROOT / "evaluator" / "daily_bar.py")
        cls.returned_metrics = evaluator.evaluate(cls.scratch, EXPERIMENT_ID)

    @classmethod
    def _build_scratch_root(cls) -> None:
        (cls.scratch / "DATA_MANIFEST.json").write_bytes(cls.manifest_bytes)
        (cls.scratch / "CORE_MANIFEST.json").write_bytes(cls.core_bytes)

        manifest = json.loads(cls.manifest_bytes)
        dataset = next(
            item
            for item in manifest["datasets"]
            if item["dataset_id"] == cls.design["dataset_ids"][0]
        )
        cls.dataset = dataset

        # The manifest's recorded checksum names the surviving snapshot file.
        snapshot = (
            ROOT / "data" / "snapshots" / dataset["dataset_id"] / f"{dataset['checksum']}.csv"
        )
        if not snapshot.is_file():
            raise AssertionError(f"Content-addressed snapshot missing: {snapshot}")
        cls.snapshot = snapshot

        target = cls.scratch / dataset["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(snapshot, target)

        strategy_target = cls.scratch / cls.design["strategy_entrypoint"]
        strategy_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / cls.design["strategy_entrypoint"], strategy_target)

        scratch_results = cls.scratch / "results" / EXPERIMENT_ID
        scratch_results.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            RESULT_DIR / "preregistration.json",
            scratch_results / "preregistration.json",
        )
        cls.scratch_results = scratch_results

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    # -- preconditions the replay depends on ------------------------------

    def test_pinned_manifest_matches_the_preregistered_hash(self) -> None:
        self.assertEqual(
            sha256_bytes(self.manifest_bytes),
            self.design["data_manifest_sha256"],
            "DATA_MANIFEST.json at the preregistered commit no longer hashes to "
            "the value E-0002 recorded; the replay inputs are not E-0002's.",
        )
        self.assertEqual(json.loads(self.manifest_bytes)["manifest_version"], "1.0.0")

    def test_evaluator_bytes_are_the_sealed_g0002_evaluator(self) -> None:
        core = json.loads(self.core_bytes)
        self.assertEqual(core["system_generation"], self.design["system_generation"])
        recorded = {
            entry["path"]: entry["sha256"]
            for component in core["sealed_components"]
            for entry in component["paths"]
        }
        self.assertEqual(
            sha256_file(ROOT / "evaluator" / "daily_bar.py"),
            recorded["evaluator/daily_bar.py"],
            "The evaluator on disk is not the one E-0002 was sealed against; "
            "a replay against different bytes proves nothing about E-0002.",
        )

    def test_snapshot_is_the_dataset_the_manifest_names(self) -> None:
        # The snapshot filename is its content hash; recompute rather than trust it.
        self.assertEqual(sha256_file(self.snapshot), self.dataset["checksum"])
        self.assertEqual(self.snapshot.stem, self.dataset["checksum"])

    def test_strategy_matches_the_preregistered_hash(self) -> None:
        self.assertEqual(
            sha256_file(ROOT / self.design["strategy_entrypoint"]),
            self.design["strategy_sha256"],
        )

    # -- the determinism claim itself -------------------------------------

    def test_recorded_metrics_match_the_backlog_baseline(self) -> None:
        self.assertEqual(
            sha256_file(RESULT_DIR / "metrics.json"), BASELINE_METRICS_SHA256
        )

    def test_replayed_outputs_are_byte_identical(self) -> None:
        for name in DETERMINISTIC_OUTPUTS:
            with self.subTest(artifact=name):
                replayed = (self.scratch_results / name).read_bytes()
                recorded = (RESULT_DIR / name).read_bytes()
                self.assertEqual(
                    sha256_bytes(replayed),
                    sha256_bytes(recorded),
                    f"{name} differs on replay: the evaluator is not deterministic "
                    "over the preregistered inputs.",
                )
                self.assertEqual(replayed, recorded)

    def test_metrics_agree_key_by_key(self) -> None:
        replayed = json.loads((self.scratch_results / "metrics.json").read_text())
        recorded = json.loads((RESULT_DIR / "metrics.json").read_text())
        self.assertEqual(sorted(replayed), sorted(recorded))
        for key in recorded:
            with self.subTest(metric=key):
                if key in INTERPRETER_SENSITIVE_METRICS:
                    self.assertTrue(
                        math.isclose(replayed[key], recorded[key], rel_tol=1e-12),
                        f"{key}: {replayed[key]!r} vs recorded {recorded[key]!r} "
                        "differ by more than float-summation noise.",
                    )
                else:
                    self.assertEqual(replayed[key], recorded[key])

    def test_returned_metrics_match_the_metrics_file(self) -> None:
        # The in-memory return value and the written artifact must not diverge.
        self.assertEqual(
            self.returned_metrics,
            json.loads((self.scratch_results / "metrics.json").read_text()),
        )

    def test_turnover_gap_is_float_summation_semantics(self) -> None:
        """Name the mechanism instead of hiding it behind a tolerance.

        `turnover` is `sum(notionals) / (sum(equities) / len(equities))`.
        `equity.csv` and `trades.csv` replay byte-identically, so the inputs to
        that division are the same numbers in the same order; only the
        summation differs. CPython 3.12 changed `sum()` over floats to
        Neumaier compensated summation (gh-100425), which is more accurate than
        the naive left-to-right addition of 3.11. Recomputing turnover both
        ways from the byte-identical artifacts shows which interpreter produced
        which value, so the residual is attributed, not waved away.
        """
        equities = [
            float(row["equity"])
            for row in csv.DictReader(
                (self.scratch_results / "equity.csv").read_text().splitlines()
            )
        ][self.design["parameter_coordinates"]["warmup_sessions"] :]
        notionals = [
            float(row["notional"])
            for row in csv.DictReader(
                (self.scratch_results / "trades.csv").read_text().splitlines()
            )
        ]
        recorded = json.loads((RESULT_DIR / "metrics.json").read_text())["turnover"]
        replayed = json.loads(
            (self.scratch_results / "metrics.json").read_text()
        )["turnover"]

        naive = sum(notionals) / (sum(equities) / len(equities))
        compensated = math.fsum(notionals) / (math.fsum(equities) / len(equities))

        self.assertEqual(
            naive,
            replayed,
            "This interpreter's plain sum() does not reproduce its own replay; "
            "the difference is then not summation semantics.",
        )
        self.assertIn(
            recorded,
            (naive, compensated),
            f"Recorded turnover {recorded!r} matches neither this interpreter's "
            f"naive sum ({naive!r}) nor exact summation ({compensated!r}); the "
            "gap is something other than float-summation semantics and must be "
            "investigated before the determinism claim is trusted.",
        )

    def test_run_log_reproduces_apart_from_the_timestamp(self) -> None:
        def without_timestamp(text: str) -> list[str]:
            return [
                line
                for line in text.splitlines()
                if not line.startswith("finished_at=")
            ]

        self.assertEqual(
            without_timestamp((self.scratch_results / "run.log").read_text()),
            without_timestamp((RESULT_DIR / "run.log").read_text()),
        )

    # -- the replay must not have touched the evidence --------------------

    def test_recorded_evidence_is_unmodified(self) -> None:
        after = {
            path.name: sha256_file(path)
            for path in sorted(RESULT_DIR.iterdir())
            if path.is_file()
        }
        self.assertEqual(self.evidence_before, after)


if __name__ == "__main__":
    unittest.main()
