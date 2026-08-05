#!/usr/bin/env python3
"""Create an immutable experiment preregistration draft."""

import argparse
import ast
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def next_experiment_id(ledger_path: Path, results_root: Path) -> str:
    maximum = 0
    with ledger_path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)["experiment_id"]
                maximum = max(maximum, int(value.split("-")[1]))
    for path in results_root.glob("E-*"):
        if path.is_dir() and path.name[2:].isdigit():
            maximum = max(maximum, int(path.name[2:]))
    return f"E-{maximum + 1:04d}"


def atomic_create(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=False)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def atomic_write(path: Path, payload: dict) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def active_evaluator_id(core_manifest: dict) -> str:
    identifiers = [
        component["component_id"]
        for component in core_manifest.get("sealed_components", [])
        if component.get("status") == "sealed"
        and str(component.get("component_id", "")).startswith("EV-")
    ]
    if len(identifiers) != 1:
        raise ValueError("Exactly one sealed evaluator must be active.")
    return identifiers[0]


def strategy_warmup_sessions(strategy_path: Path) -> int:
    tree = ast.parse(
        strategy_path.read_text(encoding="utf-8"), filename=str(strategy_path)
    )
    values = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == "WARMUP_SESSIONS"
            for target in targets
        ):
            continue
        try:
            values.append(ast.literal_eval(node.value))
        except (ValueError, TypeError):
            raise ValueError("WARMUP_SESSIONS must be an integer literal.") from None
    if len(values) != 1:
        raise ValueError("Strategy must define WARMUP_SESSIONS exactly once.")
    value = values[0]
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("WARMUP_SESSIONS must be a positive integer.")
    return value


def build_record(args, experiment_id: str, state: dict, manifest: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": "1.0.0",
        "experiment_id": experiment_id,
        "run_id": state["run"]["run_id"] or "unbound",
        "hypothesis_id": args.hypothesis,
        "parent_experiment_id": args.parent,
        "strategy_id": args.strategy,
        "status": "preregistered",
        "evidence_stage": state["objective"]["evidence_stage"],
        "created_at": now,
        "started_at": None,
        "finished_at": None,
        "intent": {
            "title": args.title,
            "rationale": args.rationale,
            "predicted_outcome": args.prediction,
        },
        "design": {
            "system_generation": state["objective"]["system_generation"],
            "evaluator_id": args.evaluator_id,
            "trial_family_id": args.trial_family,
            "trial_number": state["budget"]["trials_consumed"] + 1,
            "parameter_coordinates": {"warmup_sessions": args.warmup_sessions},
            "holdout_access": args.holdout,
            "strategy_entrypoint": args.strategy_entrypoint,
            "strategy_sha256": args.strategy_sha256,
            "initial_capital": args.initial_capital,
            "code_commit": args.commit,
            "environment_id": args.environment,
            "random_seed": args.seed,
            "time_budget_minutes": args.minutes,
            "data_manifest_version": manifest["manifest_version"],
            "data_manifest_sha256": args.data_manifest_sha256,
            "dataset_ids": args.dataset,
            "universe_id": args.universe,
            "discovery_window": None,
            "confirmation_window": None,
            "signal_timestamp_rule": args.signal_timestamp_rule,
            "execution_timestamp_rule": args.execution_timestamp_rule,
            "rebalance_rule": args.rebalance_rule,
            "holding_period": args.holding_period,
            "benchmarks": args.benchmark,
            "cost_model_id": args.cost_model,
            "risk_policy_id": args.risk_policy,
            "primary_metric": args.primary_metric,
            "secondary_metrics": [
                "sharpe_ratio",
                "max_drawdown",
                "turnover",
            ],
            "promotion_rule": {
                "operator": "all",
                "criteria": args.criterion,
            },
        },
        "results": None,
        "validity": {
            "preregistered": True,
            "trial_budget_debited": True,
            "purge_periods": args.purge_periods,
            "embargo_periods": args.embargo_periods,
            "lookahead_check": "not_run",
            "survivorship_check": "not_run",
            "leakage_check": "not_run",
            "corporate_action_check": "not_run",
            "missing_data_check": "not_run",
            "multiple_testing_adjustment": "not_run",
            "independent_review": "not_run",
        },
        "decision": {
            "outcome": "block",
            "reason": "Pending execution and evidence review.",
            "next_action": "Complete design fields, execute, and finalize the experiment.",
            "next_evidence_stage": state["objective"]["evidence_stage"],
        },
        "artifacts": [],
        "lineage": {
            "agent_id": args.agent,
            "skill_versions": {"experiment-loop": "0.1.0"},
            "tool_versions": {},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--strategy-entrypoint", required=True)
    parser.add_argument("--initial-capital", type=float, default=100000.0)
    parser.add_argument("--title", required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--prediction", required=True)
    parser.add_argument("--criterion", action="append", required=True)
    parser.add_argument("--dataset", action="append", default=[])
    parser.add_argument("--benchmark", action="append", default=["SPY"])
    parser.add_argument("--universe")
    parser.add_argument("--cost-model")
    parser.add_argument("--risk-policy")
    parser.add_argument("--parent")
    parser.add_argument("--trial-family", default="TF-0001")
    parser.add_argument("--holdout", action="store_true")
    parser.add_argument("--purge-periods", type=int)
    parser.add_argument("--embargo-periods", type=int)
    parser.add_argument("--commit")
    parser.add_argument("--environment", default="local")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--primary-metric", default="net_excess_return")
    parser.add_argument("--agent", default="autonomous-agent")
    parser.add_argument("--signal-timestamp-rule", default="After session close")
    parser.add_argument("--execution-timestamp-rule", default="Next session open")
    parser.add_argument("--rebalance-rule", default="Daily")
    parser.add_argument("--holding-period", default="Until next rebalance")
    args = parser.parse_args()

    root = args.root.resolve()
    state_path = root / "STATE.json"
    manifest_path = root / "DATA_MANIFEST.json"
    strategy_path = (root / args.strategy_entrypoint).resolve()
    if root not in strategy_path.parents or not strategy_path.is_file():
        raise ValueError("strategy_entrypoint must be an existing repository file.")
    args.strategy_sha256 = hashlib.sha256(strategy_path.read_bytes()).hexdigest()
    args.data_manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    args.warmup_sessions = strategy_warmup_sessions(strategy_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    core_manifest = json.loads((root / "CORE_MANIFEST.json").read_text(encoding="utf-8"))
    args.evaluator_id = active_evaluator_id(core_manifest)
    budget = state["budget"]
    if budget["trials_consumed"] >= budget["trial_budget"]:
        raise ValueError("Trial budget exhausted.")
    if args.holdout and budget["holdout_touches"] >= budget["holdout_touch_budget"]:
        raise ValueError("Holdout touch budget exhausted.")

    experiment_id = next_experiment_id(root / "EXPERIMENTS.jsonl", root / "results")
    record = build_record(args, experiment_id, state, manifest)
    output = root / "results" / experiment_id / "preregistration.json"
    atomic_create(output, record)
    budget["trials_consumed"] += 1
    if args.holdout:
        budget["holdout_touches"] += 1
    state["objective"]["active_experiment_id"] = experiment_id
    state["revision"] += 1
    state["updated_at"] = record["created_at"]
    state["integrity"]["validation_status"] = "pending"
    atomic_write(root / "STATE.json", state)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(json.dumps({"experiment_id": experiment_id, "path": str(output), "sha256": digest}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
