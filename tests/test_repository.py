import csv
import copy
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = load_module(
    "validate_repository", ROOT / "scripts" / "validate_repository.py"
)
bootstrap = load_module("bootstrap_run", ROOT / "scripts" / "bootstrap_run.py")
preregister = load_module(
    "preregister_experiment", ROOT / "scripts" / "preregister_experiment.py"
)
daily_bar = load_module("daily_bar", ROOT / "evaluator" / "daily_bar.py")
evidence_review = load_module(
    "record_evidence_review", ROOT / "scripts" / "record_evidence_review.py"
)
finalizer = load_module(
    "finalize_experiment", ROOT / "scripts" / "finalize_experiment.py"
)


class RepositoryContractTests(unittest.TestCase):
    def test_genesis_repository_is_valid(self):
        self.assertEqual([], validator.validate(ROOT))

    def test_canonical_json_files_parse(self):
        for relative in [
            "STATE.json",
            "DATA_MANIFEST.json",
            "CORE_MANIFEST.json",
            "schemas/state.schema.json",
            "schemas/experiment.schema.json",
            "schemas/data-manifest.schema.json",
        ]:
            with self.subTest(path=relative):
                json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_experiment_ids_are_unique(self):
        records = validator.load_ledger(ROOT / "EXPERIMENTS.jsonl", [])
        identifiers = [record["experiment_id"] for record in records]
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_pending_experiment_directories_reserve_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary)
            shutil.copy(ROOT / "EXPERIMENTS.jsonl", temp_root / "EXPERIMENTS.jsonl")
            (temp_root / "results" / "E-0001").mkdir(parents=True)
            identifier = preregister.next_experiment_id(
                temp_root / "EXPERIMENTS.jsonl", temp_root / "results"
            )
            used = {
                int(record["experiment_id"].split("-", 1)[1])
                for record in validator.load_ledger(
                    temp_root / "EXPERIMENTS.jsonl", []
                )
            }
            used.add(1)
            self.assertEqual(f"E-{max(used) + 1:04d}", identifier)

    def test_no_proven_key_in_canonical_state(self):
        state = json.loads((ROOT / "STATE.json").read_text(encoding="utf-8"))
        records = validator.load_ledger(ROOT / "EXPERIMENTS.jsonl", [])
        self.assertFalse(validator.find_key(state, "proven"))
        self.assertFalse(any(validator.find_key(record, "proven") for record in records))

    def test_bootstrap_creates_bounded_dirty_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary)
            shutil.copy(ROOT / "STATE.json", temp_root / "STATE.json")
            prepared = json.loads(
                (temp_root / "STATE.json").read_text(encoding="utf-8")
            )
            prepared["run"]["status"] = "completed"
            prepared["run"]["dirty_shutdown"] = False
            (temp_root / "STATE.json").write_text(
                json.dumps(prepared, indent=2) + "\n", encoding="utf-8"
            )
            state = bootstrap.start_run(temp_root, minutes=60, max_experiments=2)
            self.assertEqual("orienting", state["run"]["status"])
            self.assertTrue(state["run"]["dirty_shutdown"])
            self.assertEqual(60, state["budget"]["session_minutes"])
            self.assertEqual(2, state["budget"]["max_experiments"])
            self.assertIsNotNone(state["run"]["deadline_at"])

    def test_bootstrap_protects_closing_reserve(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary)
            shutil.copy(ROOT / "STATE.json", temp_root / "STATE.json")
            with self.assertRaises(ValueError):
                bootstrap.start_run(temp_root, minutes=10, max_experiments=1)

    def test_sealed_evaluator_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary) / "lab"
            shutil.copytree(ROOT, temp_root)
            evaluator_path = temp_root / "evaluator" / "daily_bar.py"
            evaluator_path.write_text(
                evaluator_path.read_text(encoding="utf-8") + "\n# unauthorized change\n",
                encoding="utf-8",
            )
            errors = validator.validate(temp_root)
            self.assertTrue(
                any("Sealed component checksum mismatch" in error for error in errors)
            )

    def test_all_core_skills_have_completion_criteria(self):
        for skill_name in validator.CORE_SKILLS:
            skill_path = ROOT / "skills" / skill_name / "SKILL.md"
            with self.subTest(skill=skill_name):
                text = skill_path.read_text(encoding="utf-8")
                self.assertIn("completion criterion", text.lower())

    def test_daily_bar_pipeline_is_replayable_immutable_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary) / "lab"
            shutil.copytree(ROOT, temp_root)
            for cache in temp_root.rglob("__pycache__"):
                shutil.rmtree(cache)
            shutil.rmtree(temp_root / "results", ignore_errors=True)
            (temp_root / "results").mkdir()
            ledger_lines = (temp_root / "EXPERIMENTS.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            (temp_root / "EXPERIMENTS.jsonl").write_text(
                ledger_lines[0] + "\n", encoding="utf-8"
            )

            data_path = temp_root / "data" / "spy.csv"
            rows = [
                ["2026-01-02", "SPY", 100, 102, 99, 101, 1000000],
                ["2026-01-05", "SPY", 102, 104, 101, 103, 1100000],
                ["2026-01-06", "SPY", 104, 106, 103, 105, 1200000],
                ["2026-01-07", "SPY", 105, 107, 104, 106, 1300000],
                ["2026-01-08", "SPY", 106, 108, 105, 107, 1400000],
            ]
            with data_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
                writer.writerows(rows)
            digest = hashlib.sha256(data_path.read_bytes()).hexdigest()

            manifest = json.loads(
                (temp_root / "DATA_MANIFEST.json").read_text(encoding="utf-8")
            )
            manifest.update(
                {
                    "integrity_status": "validated",
                    "datasets": [
                        {
                            "dataset_id": "D-0001",
                            "provider": "test-fixture",
                            "retrieval_tool": "unit-test",
                            "path": "data/spy.csv",
                            "retrieved_at": "2026-01-09T00:00:00Z",
                            "as_of": "2026-01-08T23:59:59Z",
                            "start_date": "2026-01-02",
                            "end_date": "2026-01-08",
                            "frequency": "daily",
                            "fields": ["open", "high", "low", "close", "volume"],
                            "timezone": "America/New_York",
                            "point_in_time": True,
                            "survivorship_free": True,
                            "corporate_action_policy": "Raw prices; no actions in fixture.",
                            "revision_policy": "Immutable fixture.",
                            "license": "test-only",
                            "checksum": digest,
                            "status": "validated",
                        }
                    ],
                    "universes": [
                        {
                            "universe_id": "U-0001",
                            "name": "SPY fixture",
                            "membership_rule": "SPY only",
                            "effective_dating": "Static for fixture interval",
                            "status": "validated",
                        }
                    ],
                    "cost_models": [
                        {
                            "cost_model_id": "C-0001",
                            "commission_per_share": 0.005,
                            "minimum_commission": 1.0,
                            "slippage_bps": 2.0,
                            "market_impact_bps": 0.0,
                            "status": "validated",
                        }
                    ],
                    "risk_policies": [
                        {
                            "risk_policy_id": "R-0001",
                            "max_gross_exposure": 1.0,
                            "max_position_weight": 1.0,
                            "max_drawdown": 0.5,
                            "liquidity_rule": "Fixture only",
                            "status": "validated",
                        }
                    ],
                    "validation": {
                        "validated_at": "2026-01-09T00:00:00Z",
                        "validator": "unit-test",
                        "checks": ["checksum", "calendar", "ohlc"],
                        "open_issues": [],
                    },
                }
            )
            (temp_root / "DATA_MANIFEST.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )

            state = json.loads((temp_root / "STATE.json").read_text(encoding="utf-8"))
            state["objective"]["evidence_stage"] = "baseline"
            state["objective"]["active_experiment_id"] = "E-0001"
            state["budget"]["experiments_completed"] = 0
            state["budget"]["trials_consumed"] = 0
            state["integrity"]["last_experiment_id"] = "E-0000"
            state["data"]["integrity_status"] = "validated"
            state["data"]["latest_market_as_of"] = "2026-01-08"
            args = SimpleNamespace(
                hypothesis="H-0001",
                parent=None,
                strategy="S-0002",
                title="Passive SPY evaluator baseline",
                rationale="Validate timing, costs, accounting, and finalization.",
                prediction="The first trade occurs on the second session open.",
                commit=None,
                environment="unit-test",
                seed=7,
                minutes=5,
                dataset=["D-0001"],
                universe="U-0001",
                benchmark=["SPY"],
                cost_model="C-0001",
                risk_policy="R-0001",
                primary_metric="net_excess_return",
                criterion=["Artifacts reconcile and repository validation passes."],
                agent="experiment-agent",
                trial_family="TF-0001",
                holdout=False,
                purge_periods=None,
                embargo_periods=None,
                strategy_entrypoint="strategies/S-0002/strategy.py",
                initial_capital=100000.0,
                strategy_sha256=hashlib.sha256(
                    (temp_root / "strategies/S-0002/strategy.py").read_bytes()
                ).hexdigest(),
                data_manifest_sha256=hashlib.sha256(
                    (temp_root / "DATA_MANIFEST.json").read_bytes()
                ).hexdigest(),
                evaluator_id="EV-0002",
                signal_timestamp_rule="After session close",
                execution_timestamp_rule="Next session open",
                rebalance_rule="Daily",
                holding_period="Until next rebalance",
                warmup_sessions=1,
            )
            prereg = preregister.build_record(args, "E-0001", state, manifest)
            state["budget"]["trials_consumed"] = 1
            prereg["evidence_stage"] = "baseline"
            prereg["design"].update(
                {
                    "signal_timestamp_rule": "After session close",
                    "execution_timestamp_rule": "Next session open",
                    "rebalance_rule": "Daily",
                    "holding_period": "Until next rebalance",
                }
            )
            result_dir = temp_root / "results" / "E-0001"
            result_dir.mkdir()
            (result_dir / "preregistration.json").write_text(
                json.dumps(prereg, indent=2) + "\n", encoding="utf-8"
            )
            (temp_root / "STATE.json").write_text(
                json.dumps(state, indent=2) + "\n", encoding="utf-8"
            )

            metrics = daily_bar.evaluate(temp_root, "E-0001")
            self.assertGreater(metrics["trade_count"], 0)
            expected_benchmark = rows[-1][5] / rows[1][2] - 1
            self.assertAlmostEqual(
                expected_benchmark, metrics["benchmark_metric_value"]
            )
            with (result_dir / "trades.csv").open(encoding="utf-8") as handle:
                trades = list(csv.DictReader(handle))
            self.assertEqual("2026-01-05", trades[0]["date"])
            with self.assertRaises(FileExistsError):
                daily_bar.evaluate(temp_root, "E-0001")

            review = evidence_review.record_review(
                temp_root,
                "E-0001",
                "independent-reviewer",
                "keep",
                ["Timing and accounting artifacts match the EV-0001 contract."],
                "Add a strategy-specific null baseline.",
                False,
            )
            self.assertEqual("passed", review["independent_review"])
            record = finalizer.finalize(
                temp_root,
                "E-0001",
                "keep",
                "Baseline evaluator contract passed.",
                "Add a strategy-specific null baseline.",
                "baseline",
            )
            self.assertEqual("completed", record["status"])
            self.assertEqual([], validator.validate(temp_root))

            state_after = json.loads(
                (temp_root / "STATE.json").read_text(encoding="utf-8")
            )
            completed = state_after["budget"]["experiments_completed"]
            replayed = finalizer.finalize(
                temp_root,
                "E-0001",
                "keep",
                "Baseline evaluator contract passed.",
                "Add a strategy-specific null baseline.",
                "baseline",
            )
            self.assertEqual(record, replayed)
            state_replayed = json.loads(
                (temp_root / "STATE.json").read_text(encoding="utf-8")
            )
            self.assertEqual(completed, state_replayed["budget"]["experiments_completed"])
            self.assertEqual("completed", state_replayed["run"]["status"])
            self.assertFalse(state_replayed["run"]["dirty_shutdown"])
            self.assertEqual(
                "Add a strategy-specific null baseline.",
                state_replayed["next_actions"][0]["description"],
            )

    def test_historical_generation_remains_valid_after_generation_bump(self):
        # Assert the ordering this test is named for, deriving both sides.
        # Naming either generation as a literal is what broke this test: the
        # one that exists to prove a generation bump is safe was itself failed
        # by one.
        records = validator.load_ledger(ROOT / "EXPERIMENTS.jsonl", [])
        recorded = {
            record["design"]["system_generation"] for record in records
        }
        ledger_numbers = {
            number
            for number in (validator.generation_number(value) for value in recorded)
            if number is not None
        }
        self.assertEqual(
            len(ledger_numbers),
            len(recorded),
            f"EXPERIMENTS.jsonl carries a malformed system_generation: {recorded}",
        )
        self.assertTrue(ledger_numbers, "EXPERIMENTS.jsonl records no generation.")

        current = json.loads(
            (ROOT / "CORE_MANIFEST.json").read_text(encoding="utf-8")
        )["system_generation"]
        current_number = validator.generation_number(current)
        self.assertIsNotNone(
            current_number,
            f"CORE_MANIFEST.json system_generation {current!r} is malformed",
        )

        # The ledger is append-only (ADR-0001), so the oldest generation in it
        # only ever recedes further behind the manifest.
        self.assertLess(
            min(ledger_numbers),
            current_number,
            f"The manifest ({current}) has not moved past the oldest generation "
            "in the ledger, so this test is not exercising a generation bump.",
        )
        self.assertEqual([], validator.validate(ROOT))

    def test_evaluation_start_is_first_executable_session(self):
        dates = ["2026-01-02", "2026-01-05", "2026-01-06"]
        bars = {
            "2026-01-02": {"SPY": {"open": 100.0, "close": 101.0}},
            "2026-01-05": {"SPY": {"open": 102.0, "close": 103.0}},
            "2026-01-06": {"SPY": {"open": 104.0, "close": 105.0}},
        }
        start, end, result = daily_bar.benchmark_interval(dates, bars, "SPY", 1)
        self.assertEqual("2026-01-05", start)
        self.assertEqual("2026-01-06", end)
        self.assertAlmostEqual(105.0 / 102.0 - 1, result)

    def test_preregistered_warmup_moves_common_evaluation_start(self):
        dates = [
            "2026-01-02",
            "2026-01-05",
            "2026-01-06",
            "2026-01-07",
            "2026-01-08",
        ]
        bars = {
            date: {"SPY": {"open": 100.0 + index, "close": 100.5 + index}}
            for index, date in enumerate(dates)
        }
        start, end, result = daily_bar.benchmark_interval(dates, bars, "SPY", 3)
        self.assertEqual("2026-01-07", start)
        self.assertEqual("2026-01-08", end)
        self.assertAlmostEqual(104.5 / 103.0 - 1, result)

    def test_pending_experiment_must_use_current_sealed_evaluator(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary) / "lab"
            shutil.copytree(ROOT, temp_root)
            pending = json.loads(
                (
                    temp_root / "results" / "E-0001" / "preregistration.json"
                ).read_text(encoding="utf-8")
            )
            pending["experiment_id"] = "E-9999"
            pending["design"]["system_generation"] = "G-0002"
            pending["design"]["evaluator_id"] = "EV-0001"
            pending_dir = temp_root / "results" / "E-9999"
            pending_dir.mkdir()
            (pending_dir / "preregistration.json").write_text(
                json.dumps(pending, indent=2) + "\n", encoding="utf-8"
            )
            errors = validator.validate(temp_root)
            self.assertTrue(
                any(
                    "does not use the current sealed evaluator" in error
                    for error in errors
                )
            )

    def test_strategy_warmup_is_pinned_and_runtime_mismatch_is_rejected(self):
        strategy_path = ROOT / "strategies" / "S-0002" / "strategy.py"
        self.assertEqual(1, preregister.strategy_warmup_sessions(strategy_path))
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary) / "lab"
            shutil.copytree(ROOT, temp_root)
            pending = json.loads(
                (
                    temp_root / "results" / "E-0001" / "preregistration.json"
                ).read_text(encoding="utf-8")
            )
            pending["experiment_id"] = "E-9998"
            pending["design"]["system_generation"] = "G-0002"
            pending["design"]["evaluator_id"] = "EV-0002"
            pending["design"]["strategy_id"] = "S-0002"
            pending["design"]["strategy_entrypoint"] = (
                "strategies/S-0002/strategy.py"
            )
            pending["design"]["parameter_coordinates"] = {"warmup_sessions": 2}
            copied_strategy = (
                temp_root / "strategies" / "S-0002" / "strategy.py"
            )
            pending["design"]["strategy_sha256"] = hashlib.sha256(
                copied_strategy.read_bytes()
            ).hexdigest()
            pending_dir = temp_root / "results" / "E-9998"
            pending_dir.mkdir()
            (pending_dir / "preregistration.json").write_text(
                json.dumps(pending, indent=2) + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "does not match"):
                daily_bar.evaluate(temp_root, "E-9998")


if __name__ == "__main__":
    unittest.main()
