#!/usr/bin/env python3
"""Verify immutable outputs, append the experiment ledger, and advance state."""

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PROMOTION_CHECKS = [
    "lookahead_check",
    "survivorship_check",
    "leakage_check",
    "corporate_action_check",
    "missing_data_check",
]


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def load_ledger(path: Path) -> dict[str, dict]:
    records = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                records[record["experiment_id"]] = record
    return records


def verify_artifacts(root: Path, result_dir: Path) -> list[dict]:
    manifest_path = result_dir / "artifact-manifest.json"
    manifest = read_json(manifest_path)
    artifacts = []
    for item in manifest["artifacts"]:
        path = (root / item["path"]).resolve()
        if root.resolve() not in path.parents:
            raise ValueError("Artifact path escapes repository.")
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256(path) != item["sha256"]:
            raise ValueError(f"Artifact checksum mismatch: {item['path']}")
        artifacts.append(item)
    artifacts.append(
        {
            "path": str(manifest_path.relative_to(root)),
            "sha256": sha256(manifest_path),
            "media_type": "application/json",
        }
    )
    review_path = result_dir / "review.json"
    if review_path.exists():
        artifacts.append(
            {
                "path": str(review_path.relative_to(root)),
                "sha256": sha256(review_path),
                "media_type": "application/json",
            }
        )
    return artifacts


def finalize(
    root: Path,
    experiment_id: str,
    outcome: str,
    reason: str,
    next_action: str,
    next_stage: str,
) -> dict:
    ledger_path = root / "EXPERIMENTS.jsonl"
    ledger = load_ledger(ledger_path)
    if experiment_id in ledger:
        existing = ledger[experiment_id]
        if existing["decision"]["outcome"] != outcome:
            raise ValueError("Existing final outcome differs from requested outcome.")
        update_state(root, existing)
        return existing
    result_dir = root / "results" / experiment_id
    prereg = read_json(result_dir / "preregistration.json")
    metrics = read_json(result_dir / "metrics.json")
    validity = read_json(result_dir / "validity.json")
    artifacts = verify_artifacts(root, result_dir)
    review_path = result_dir / "review.json"
    review = read_json(review_path) if review_path.exists() else None

    if outcome == "promote":
        if review is None or review["decision"] != "promote":
            raise ValueError("Promotion requires a matching independent review.")
        if review.get("promotion_criteria_passed") is not True:
            raise ValueError("Promotion criteria were not explicitly confirmed.")
        failed = [
            check for check in PROMOTION_CHECKS if validity.get(check) != "passed"
        ]
        if failed:
            raise ValueError(f"Promotion blocked by validity checks: {failed}")
        validity["independent_review"] = "passed"
    elif review is not None:
        if review["decision"] != outcome:
            raise ValueError("Final outcome disagrees with independent review.")
        validity["independent_review"] = review["independent_review"]

    finalization_path = result_dir / "finalization.json"
    if finalization_path.exists():
        final_record = read_json(finalization_path)
        requested = {
            "outcome": outcome,
            "reason": reason,
            "next_action": next_action,
            "next_evidence_stage": next_stage,
        }
        if final_record["decision"] != requested:
            raise ValueError("Existing finalization decision differs from requested finalization.")
    else:
        final_record = {
            **prereg,
            "status": "completed",
            "started_at": prereg["created_at"],
            "finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "results": metrics,
            "validity": validity,
            "decision": {
                "outcome": outcome,
                "reason": reason,
                "next_action": next_action,
                "next_evidence_stage": next_stage,
            },
            "artifacts": artifacts,
        }
        atomic_write_json(finalization_path, final_record)

    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(final_record, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())

    update_state(root, final_record)
    return final_record


def update_state(root: Path, final_record: dict) -> None:
    state_path = root / "STATE.json"
    state = read_json(state_path)
    experiment_id = final_record["experiment_id"]
    if state["integrity"]["last_experiment_id"] == experiment_id:
        return
    decision = final_record["decision"]
    outcome = decision["outcome"]
    next_stage = decision["next_evidence_stage"]
    state["revision"] += 1
    state["updated_at"] = final_record["finished_at"]
    state["objective"]["active_experiment_id"] = None
    if outcome in {"promote", "demote"}:
        state["objective"]["evidence_stage"] = next_stage
    if outcome == "promote":
        state["objective"]["champion_strategy_id"] = final_record["strategy_id"]
    state["budget"]["experiments_completed"] += 1
    state["handoff"]["summary"] = (
        f"{experiment_id} finalized as {outcome}: {decision['reason']}"
    )
    state["handoff"]["last_verified_artifacts"] = [
        item["path"] for item in final_record["artifacts"]
    ]
    state["integrity"]["last_experiment_id"] = experiment_id
    state["integrity"]["validation_status"] = "pending"
    atomic_write_json(state_path, state)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_id")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--outcome",
        required=True,
        choices=["keep", "discard", "iterate", "promote", "demote", "block"],
    )
    parser.add_argument("--reason", required=True)
    parser.add_argument("--next-action", required=True)
    parser.add_argument(
        "--next-stage",
        required=True,
        choices=["bootstrap", "baseline", "discovery", "out_of_sample", "walk_forward", "paper"],
    )
    args = parser.parse_args()
    record = finalize(
        args.root.resolve(),
        args.experiment_id,
        args.outcome,
        args.reason,
        args.next_action,
        args.next_stage,
    )
    print(
        json.dumps(
            {
                "experiment_id": record["experiment_id"],
                "status": record["status"],
                "outcome": record["decision"]["outcome"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
