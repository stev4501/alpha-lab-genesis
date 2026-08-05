#!/usr/bin/env python3
"""Record a fresh-agent evidence review without modifying evaluator artifacts."""

import argparse
import json
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


def record_review(
    root: Path,
    experiment_id: str,
    reviewer_id: str,
    decision: str,
    findings: list[str],
    next_action: str,
    promotion_criteria_passed: bool,
) -> dict:
    result_dir = root / "results" / experiment_id
    output = result_dir / "review.json"
    if output.exists():
        raise FileExistsError("Evidence review is immutable and already exists.")
    prereg = read_json(result_dir / "preregistration.json")
    validity = read_json(result_dir / "validity.json")
    metrics = read_json(result_dir / "metrics.json")
    if reviewer_id == prereg["lineage"]["agent_id"]:
        raise ValueError("Independent reviewer must differ from the experiment agent.")
    failed = [
        check for check in PROMOTION_CHECKS if validity.get(check) != "passed"
    ]
    if decision == "promote" and failed:
        raise ValueError(f"Promotion blocked by validity checks: {failed}")
    if decision == "promote" and not findings:
        raise ValueError("Promotion review must record at least one substantive finding.")
    if decision == "promote" and not promotion_criteria_passed:
        raise ValueError("Promotion requires explicit confirmation of every preregistered criterion.")
    payload = {
        "schema_version": "1.0.0",
        "experiment_id": experiment_id,
        "reviewer_id": reviewer_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "decision": decision,
        "findings": findings,
        "next_action": next_action,
        "independent_review": "passed",
        "promotion_criteria_passed": promotion_criteria_passed,
        "reviewed_primary_metric": prereg["design"]["primary_metric"],
        "reviewed_primary_metric_value": metrics["primary_metric_value"],
        "validity_failures": failed,
    }
    with output.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_id")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--reviewer", required=True)
    parser.add_argument(
        "--decision",
        required=True,
        choices=["keep", "discard", "iterate", "promote", "demote", "block"],
    )
    parser.add_argument("--finding", action="append", default=[])
    parser.add_argument("--next-action", required=True)
    parser.add_argument("--promotion-criteria-passed", action="store_true")
    args = parser.parse_args()
    payload = record_review(
        args.root.resolve(),
        args.experiment_id,
        args.reviewer,
        args.decision,
        args.finding,
        args.next_action,
        args.promotion_criteria_passed,
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
