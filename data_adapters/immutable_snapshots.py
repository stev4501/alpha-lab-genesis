"""Append-only, content-addressed market-data snapshot registry."""

from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


DATASET_ID = re.compile(r"^D-[0-9]{4,}$")
SERIES_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
INDEX_PATH = Path("data/snapshots/index.jsonl")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone.")
    return parsed.astimezone(timezone.utc)


def canonical_timestamp(value: str) -> str:
    return parse_timestamp(value).isoformat().replace("+00:00", "Z")


def load_index(root: Path) -> list[dict]:
    path = root / INDEX_PATH
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid snapshot index line {line_number}: {exc}") from exc
        records.append(record)
    return records


def validate_record(root: Path, record: dict) -> list[str]:
    errors = []
    required = {
        "dataset_id",
        "series_id",
        "as_of",
        "retrieved_at",
        "source_path",
        "snapshot_path",
        "sha256",
        "bytes",
    }
    missing = sorted(required - set(record))
    if missing:
        return [f"Snapshot record missing fields: {', '.join(missing)}"]
    if not DATASET_ID.fullmatch(str(record["dataset_id"])):
        errors.append(f"Invalid dataset_id: {record['dataset_id']}")
    if not SERIES_ID.fullmatch(str(record["series_id"])):
        errors.append(f"Invalid series_id: {record['series_id']}")
    try:
        as_of = parse_timestamp(record["as_of"])
        retrieved_at = parse_timestamp(record["retrieved_at"])
        if retrieved_at < as_of:
            errors.append("retrieved_at cannot precede as_of.")
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    snapshot_path = root / record["snapshot_path"]
    try:
        snapshot_path.resolve().relative_to(root.resolve())
    except ValueError:
        errors.append("Snapshot path escapes the repository.")
        return errors
    if not snapshot_path.is_file():
        errors.append(f"Snapshot file missing: {record['snapshot_path']}")
        return errors
    if snapshot_path.stat().st_size != record["bytes"]:
        errors.append(f"Snapshot byte count mismatch: {record['dataset_id']}")
    if sha256(snapshot_path) != record["sha256"]:
        errors.append(f"Snapshot checksum mismatch: {record['dataset_id']}")
    return errors


def validate_registry(root: Path) -> list[str]:
    errors = []
    records = load_index(root)
    dataset_ids = []
    snapshot_paths = []
    for record in records:
        errors.extend(validate_record(root, record))
        dataset_ids.append(record.get("dataset_id"))
        snapshot_paths.append(record.get("snapshot_path"))
    if len(dataset_ids) != len(set(dataset_ids)):
        errors.append("Snapshot dataset IDs must be unique.")
    if len(snapshot_paths) != len(set(snapshot_paths)):
        errors.append("Snapshot paths must be unique.")
    return errors


def _append_record(index_path: Path, record: dict) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def registry_lock(root: Path):
    lock_name = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()
    lock_path = Path(tempfile.gettempdir()) / f"alpha-lab-snapshots-{lock_name}.lock"
    with lock_path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def register_snapshot(
    root: Path,
    source_path: Path,
    dataset_id: str,
    series_id: str,
    as_of: str,
    retrieved_at: str,
) -> dict:
    root = root.resolve()
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if not DATASET_ID.fullmatch(dataset_id):
        raise ValueError("dataset_id must match D-NNNN.")
    if not SERIES_ID.fullmatch(series_id):
        raise ValueError("series_id contains unsupported characters.")
    as_of = canonical_timestamp(as_of)
    retrieved_at = canonical_timestamp(retrieved_at)
    if parse_timestamp(retrieved_at) < parse_timestamp(as_of):
        raise ValueError("retrieved_at cannot precede as_of.")
    content_hash = sha256(source_path)
    extension = source_path.suffix.lower() or ".bin"
    relative_snapshot = (
        Path("data")
        / "snapshots"
        / dataset_id
        / f"{content_hash}{extension}"
    )
    snapshot_path = root / relative_snapshot
    record = {
        "dataset_id": dataset_id,
        "series_id": series_id,
        "as_of": as_of,
        "retrieved_at": retrieved_at,
        "source_path": str(source_path.relative_to(root)),
        "snapshot_path": relative_snapshot.as_posix(),
        "sha256": content_hash,
        "bytes": source_path.stat().st_size,
    }
    with registry_lock(root):
        existing = load_index(root)
        same_id = [item for item in existing if item.get("dataset_id") == dataset_id]
        if same_id:
            if same_id == [record] and validate_record(root, record) == []:
                return record
            raise FileExistsError(
                f"{dataset_id} is already registered with different data."
            )
        snapshot_path.parent.mkdir(parents=True, exist_ok=False)
        with tempfile.NamedTemporaryFile(
            dir=snapshot_path.parent, prefix=".snapshot-", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            shutil.copyfile(source_path, temporary_path)
            if sha256(temporary_path) != content_hash:
                raise IOError("Snapshot checksum changed during copy.")
            os.replace(temporary_path, snapshot_path)
        finally:
            temporary_path.unlink(missing_ok=True)
        _append_record(root / INDEX_PATH, record)
    return record


def resolve_as_of(root: Path, series_id: str, as_of: str) -> dict:
    cutoff = parse_timestamp(as_of)
    candidates = [
        record
        for record in load_index(root)
        if record.get("series_id") == series_id
        and parse_timestamp(record["as_of"]) <= cutoff
        and parse_timestamp(record["retrieved_at"]) <= cutoff
    ]
    if not candidates:
        raise LookupError(f"No {series_id} snapshot exists at or before {as_of}.")
    selected = max(
        candidates,
        key=lambda record: (
            parse_timestamp(record["as_of"]),
            parse_timestamp(record["retrieved_at"]),
            record["dataset_id"],
        ),
    )
    errors = validate_record(root, selected)
    if errors:
        raise ValueError("; ".join(errors))
    return selected
