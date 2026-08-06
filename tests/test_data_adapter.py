import csv
import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path

from data_adapters.immutable_snapshots import (
    load_index,
    register_snapshot,
    resolve_as_of,
    validate_registry,
)
from scripts.normalize_finance_ohlcv import normalize

ROOT = Path(__file__).resolve().parents[1]


def register_worker(arguments):
    return register_snapshot(*arguments)["dataset_id"]


class ImmutableSnapshotTests(unittest.TestCase):
    def write_source(self, root: Path, name: str, body: str) -> Path:
        source = root / "incoming" / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(body, encoding="utf-8")
        return source

    def test_registration_is_immutable_idempotent_and_as_of_resolvable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first_source = self.write_source(root, "first.csv", "date,close\n1,100\n")
            first = register_snapshot(
                root,
                first_source,
                "D-0001",
                "SPY-1day",
                "2026-01-02T21:00:00Z",
                "2026-01-02T22:00:00Z",
            )
            self.assertEqual(
                first,
                register_snapshot(
                    root,
                    first_source,
                    "D-0001",
                    "SPY-1day",
                    "2026-01-02T21:00:00Z",
                    "2026-01-02T22:00:00Z",
                ),
            )
            first_source.write_text("date,close\n1,999\n", encoding="utf-8")
            self.assertNotEqual(
                first_source.read_bytes(),
                (root / first["snapshot_path"]).read_bytes(),
            )

            second_source = self.write_source(root, "second.csv", "date,close\n2,101\n")
            second = register_snapshot(
                root,
                second_source,
                "D-0002",
                "SPY-1day",
                "2026-01-05T21:00:00Z",
                "2026-01-05T22:00:00Z",
            )
            self.assertEqual(
                "D-0001",
                resolve_as_of(
                    root, "SPY-1day", "2026-01-04T12:00:00Z"
                )["dataset_id"],
            )
            self.assertEqual(
                "D-0001",
                resolve_as_of(
                    root, "SPY-1day", "2026-01-05T21:30:00Z"
                )["dataset_id"],
            )
            self.assertEqual(
                second,
                resolve_as_of(root, "SPY-1day", "2026-01-06T12:00:00Z"),
            )
            self.assertEqual(2, len(load_index(root)))
            self.assertEqual([], validate_registry(root))

    def test_dataset_id_cannot_be_reused_for_different_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self.write_source(root, "first.csv", "a\n1\n")
            second = self.write_source(root, "second.csv", "a\n2\n")
            register_snapshot(
                root,
                first,
                "D-0001",
                "SPY-1day",
                "2026-01-02T21:00:00Z",
                "2026-01-02T22:00:00Z",
            )
            with self.assertRaises(FileExistsError):
                register_snapshot(
                    root,
                    second,
                    "D-0001",
                    "SPY-1day",
                    "2026-01-03T21:00:00Z",
                    "2026-01-03T22:00:00Z",
                )

    def test_resolution_rejects_future_only_and_tampered_snapshots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.write_source(root, "source.csv", "a\n1\n")
            record = register_snapshot(
                root,
                source,
                "D-0001",
                "SPY-1day",
                "2026-01-02T21:00:00Z",
                "2026-01-02T22:00:00Z",
            )
            with self.assertRaises(LookupError):
                resolve_as_of(root, "SPY-1day", "2026-01-01T21:00:00Z")
            (root / record["snapshot_path"]).write_text("tampered\n", encoding="utf-8")
            self.assertTrue(
                any("checksum mismatch" in error for error in validate_registry(root))
            )
            with self.assertRaises(ValueError):
                resolve_as_of(root, "SPY-1day", "2026-01-03T21:00:00Z")

    def test_registration_rejects_retrieval_before_market_as_of(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.write_source(root, "source.csv", "a\n1\n")
            with self.assertRaisesRegex(ValueError, "retrieved_at cannot precede as_of"):
                register_snapshot(
                    root,
                    source,
                    "D-0001",
                    "SPY-1day",
                    "2026-01-02T22:00:00Z",
                    "2026-01-02T21:00:00Z",
                )

    def test_concurrent_exact_retries_are_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.write_source(root, "source.csv", "a\n1\n")
            arguments = (
                root,
                source,
                "D-0001",
                "SPY-1day",
                "2026-01-02T21:00:00Z",
                "2026-01-02T22:00:00Z",
            )
            with multiprocessing.get_context("fork").Pool(2) as pool:
                results = pool.map(register_worker, [arguments, arguments])
            self.assertEqual(["D-0001", "D-0001"], results)
            self.assertEqual(1, len(load_index(root)))
            self.assertEqual([], validate_registry(root))

    def test_manifest_datasets_use_registered_snapshots(self):
        manifest = json.loads((ROOT / "DATA_MANIFEST.json").read_text(encoding="utf-8"))
        records = {item["dataset_id"]: item for item in load_index(ROOT)}
        self.assertEqual(
            {"D-0001", "D-0002"},
            {item["dataset_id"] for item in manifest["datasets"]},
        )
        for dataset in manifest["datasets"]:
            with self.subTest(dataset_id=dataset["dataset_id"]):
                record = records[dataset["dataset_id"]]
                self.assertEqual(record["snapshot_path"], dataset["path"])
                self.assertEqual(record["sha256"], dataset["checksum"])
                self.assertEqual(record["as_of"], dataset["as_of"])
                self.assertEqual(record["retrieved_at"], dataset["retrieved_at"])
        self.assertEqual([], validate_registry(ROOT))

    def test_d0002_shape_overlap_and_later_coverage(self):
        manifest = json.loads((ROOT / "DATA_MANIFEST.json").read_text(encoding="utf-8"))
        datasets = {item["dataset_id"]: item for item in manifest["datasets"]}
        with (ROOT / datasets["D-0001"]["path"]).open(newline="") as handle:
            d1 = {row["date"]: row for row in csv.DictReader(handle)}
        with (ROOT / datasets["D-0002"]["path"]).open(newline="") as handle:
            d2_rows = list(csv.DictReader(handle))
        d2 = {row["date"]: row for row in d2_rows}

        self.assertEqual(650, len(d2_rows))
        self.assertEqual(650, len(d2))
        self.assertEqual("2024-01-02", d2_rows[0]["date"])
        self.assertEqual("2026-08-05", d2_rows[-1]["date"])
        self.assertEqual(sorted(d2), [row["date"] for row in d2_rows])
        self.assertEqual(set(d1), set(d1) & set(d2))
        self.assertEqual(502, len(set(d1) & set(d2)))
        later_dates = sorted(set(d2) - set(d1))
        self.assertEqual(148, len(later_dates))
        self.assertEqual("2026-01-02", later_dates[0])
        self.assertTrue(all(date > max(d1) for date in later_dates))
        for date, row in d1.items():
            self.assertEqual(row, d2[date])
        for row in d2_rows:
            self.assertEqual("SPY", row["symbol"])
            open_, high, low, close, volume = (
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row["volume"]),
            )
            self.assertGreater(min(open_, high, low, close), 0)
            self.assertLessEqual(low, min(open_, close))
            self.assertGreaterEqual(high, max(open_, close))
            self.assertGreaterEqual(volume, 0)

    def test_d0002_raw_provenance_reproduces_snapshot(self):
        provenance = json.loads(
            (ROOT / "data/provenance/D-0002.json").read_text(encoding="utf-8")
        )
        raw = ROOT / provenance["raw_artifact"]["path"]
        expected = ROOT / provenance["normalized_artifact"]["path"]
        with tempfile.TemporaryDirectory() as temporary:
            reproduced = Path(temporary) / "normalized.csv"
            normalize(raw, reproduced, provenance["normalization"]["symbol"])
            self.assertEqual(expected.read_bytes(), reproduced.read_bytes())
