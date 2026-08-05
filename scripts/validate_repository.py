#!/usr/bin/env python3
"""Validate Alpha Lab's deterministic repository and handoff contracts."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


REQUIRED_FILES = [
    "MISSION.md",
    "CONTEXT.md",
    "STATE.json",
    "EXPERIMENTS.jsonl",
    "HYPOTHESES.md",
    "DECISIONS.md",
    "FAILURES.md",
    "DATA_MANIFEST.json",
    "CORE_MANIFEST.json",
    "schemas/state.schema.json",
    "schemas/experiment.schema.json",
    "schemas/data-manifest.schema.json",
]
CORE_SKILLS = {
    "genesis-orchestrator",
    "hypothesis-engine",
    "experiment-loop",
    "data-integrity",
    "evidence-gate",
    "paper-execution",
    "memory-handoff",
    "skill-lifecycle-governance",
    "anti-degradation-triage",
}
EVIDENCE_STAGES = {
    "bootstrap",
    "baseline",
    "discovery",
    "out_of_sample",
    "walk_forward",
    "paper",
}
EXPERIMENT_STATUSES = {
    "preregistered",
    "running",
    "completed",
    "failed",
    "aborted",
    "blocked",
}
EXPERIMENT_FIELDS = {
    "schema_version",
    "experiment_id",
    "run_id",
    "hypothesis_id",
    "parent_experiment_id",
    "strategy_id",
    "status",
    "evidence_stage",
    "created_at",
    "started_at",
    "finished_at",
    "intent",
    "design",
    "results",
    "validity",
    "decision",
    "artifacts",
    "lineage",
}
DESIGN_FIELDS = {
    "system_generation",
    "evaluator_id",
    "trial_family_id",
    "trial_number",
    "parameter_coordinates",
    "holdout_access",
    "strategy_entrypoint",
    "strategy_sha256",
    "initial_capital",
    "code_commit",
    "environment_id",
    "random_seed",
    "time_budget_minutes",
    "data_manifest_version",
    "data_manifest_sha256",
    "dataset_ids",
    "universe_id",
    "discovery_window",
    "confirmation_window",
    "signal_timestamp_rule",
    "execution_timestamp_rule",
    "rebalance_rule",
    "holding_period",
    "benchmarks",
    "cost_model_id",
    "risk_policy_id",
    "primary_metric",
    "secondary_metrics",
    "promotion_rule",
}
VALIDITY_FIELDS = {
    "preregistered",
    "trial_budget_debited",
    "purge_periods",
    "embargo_periods",
    "lookahead_check",
    "survivorship_check",
    "leakage_check",
    "corporate_action_check",
    "missing_data_check",
    "multiple_testing_adjustment",
    "independent_review",
}


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: {exc}")
        return {}


def load_ledger(path: Path, errors: list[str]) -> list[dict]:
    records = []
    try:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    errors.append(f"{path}:{number}: {exc}")
    except OSError as exc:
        errors.append(f"{path}: {exc}")
    return records


def find_key(value, forbidden: str) -> bool:
    if isinstance(value, dict):
        return forbidden in value or any(find_key(v, forbidden) for v in value.values())
    if isinstance(value, list):
        return any(find_key(item, forbidden) for item in value)
    return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generation_number(value: object) -> int | None:
    if not isinstance(value, str) or not re.fullmatch(r"G-[0-9]{4,}", value):
        return None
    return int(value.split("-", 1)[1])


def parse_skill_frontmatter(path: Path, errors: list[str]) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append(f"{path}: missing YAML frontmatter")
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        errors.append(f"{path}: unterminated YAML frontmatter")
        return {}
    values = {}
    for raw_line in parts[1].splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in {"name", "version"}:
            values[key] = value.strip().strip("'\"")
    return values


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    if errors:
        return errors

    state = load_json(root / "STATE.json", errors)
    manifest = load_json(root / "DATA_MANIFEST.json", errors)
    core_manifest = load_json(root / "CORE_MANIFEST.json", errors)
    sealed_evaluator_ids = {
        component.get("component_id")
        for component in core_manifest.get("sealed_components", [])
        if component.get("status") == "sealed"
        and isinstance(component.get("component_id"), str)
        and component["component_id"].startswith("EV-")
    }
    if len(sealed_evaluator_ids) != 1:
        errors.append("Exactly one sealed evaluator must be active.")
        active_evaluator_id = None
    else:
        active_evaluator_id = next(iter(sealed_evaluator_ids))
    schemas = [
        load_json(root / "schemas" / name, errors)
        for name in [
            "state.schema.json",
            "experiment.schema.json",
            "data-manifest.schema.json",
        ]
    ]
    records = load_ledger(root / "EXPERIMENTS.jsonl", errors)
    preregistrations = []
    for prereg_path in sorted((root / "results").glob("E-*/preregistration.json")):
        preregistrations.append(load_json(prereg_path, errors))
    if errors:
        return errors

    if any(schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" for schema in schemas):
        errors.append("Every schema must declare JSON Schema draft 2020-12.")

    if state.get("schema_version") != "1.0.0":
        errors.append("STATE.json schema_version must be 1.0.0.")
    if state.get("objective", {}).get("evidence_stage") not in EVIDENCE_STAGES:
        errors.append("STATE.json contains an invalid evidence stage.")
    if find_key(state, "proven") or any(find_key(record, "proven") for record in records):
        errors.append("Canonical state and experiments may not contain a 'proven' key.")

    action_ids = {item.get("action_id") for item in state.get("next_actions", [])}
    next_action = state.get("handoff", {}).get("next_action_id")
    if next_action is not None and next_action not in action_ids:
        errors.append("handoff.next_action_id does not reference next_actions.")

    budget = state.get("budget", {})
    if budget.get("used_minutes", 0) > budget.get("session_minutes", 0):
        errors.append("used_minutes exceeds session_minutes.")
    if state.get("run", {}).get("reserve_minutes", 0) < 5:
        errors.append("Closing reserve must be at least 5 minutes.")
    if budget.get("trials_consumed", 0) > budget.get("trial_budget", 0):
        errors.append("trials_consumed exceeds trial_budget.")
    if budget.get("holdout_touches", 0) > budget.get("holdout_touch_budget", 0):
        errors.append("holdout_touches exceeds holdout_touch_budget.")
    if state.get("objective", {}).get("system_generation") != core_manifest.get("system_generation"):
        errors.append("STATE.json and CORE_MANIFEST.json system generation disagree.")

    current_generation_number = generation_number(core_manifest.get("system_generation"))
    if current_generation_number is None:
        errors.append("CORE_MANIFEST.json contains an invalid system generation.")

    experiment_ids = []
    for index, record in enumerate(records, start=1):
        missing = EXPERIMENT_FIELDS - set(record)
        if missing:
            errors.append(f"Experiment line {index} missing: {sorted(missing)}")
        experiment_id = record.get("experiment_id")
        experiment_ids.append(experiment_id)
        if not isinstance(experiment_id, str) or not re.fullmatch(r"E-[0-9]{4,}", experiment_id):
            errors.append(f"Experiment line {index} has invalid experiment_id.")
        if record.get("status") not in EXPERIMENT_STATUSES:
            errors.append(f"Experiment {experiment_id} has invalid status.")
        if record.get("evidence_stage") not in EVIDENCE_STAGES:
            errors.append(f"Experiment {experiment_id} has invalid evidence stage.")
        if record.get("validity", {}).get("preregistered") is not True:
            errors.append(f"Experiment {experiment_id} was not preregistered.")
        missing_design = DESIGN_FIELDS - set(record.get("design", {}))
        if missing_design:
            errors.append(f"Experiment {experiment_id} design missing: {sorted(missing_design)}")
        missing_validity = VALIDITY_FIELDS - set(record.get("validity", {}))
        if missing_validity:
            errors.append(f"Experiment {experiment_id} validity missing: {sorted(missing_validity)}")
        record_generation = record.get("design", {}).get("system_generation")
        record_generation_number = generation_number(record_generation)
        if record_generation_number is None:
            errors.append(f"Experiment {experiment_id} has an invalid system generation.")
        elif (
            current_generation_number is not None
            and record_generation_number > current_generation_number
        ):
            errors.append(f"Experiment {experiment_id} belongs to a future system generation.")
        if not record.get("design", {}).get("promotion_rule", {}).get("criteria"):
            errors.append(f"Experiment {experiment_id} lacks promotion criteria.")
        if record.get("status") == "completed":
            if record.get("results") is None:
                errors.append(f"Completed experiment {experiment_id} lacks results.")
            if not record.get("artifacts"):
                errors.append(f"Completed experiment {experiment_id} lacks artifacts.")
            for artifact in record.get("artifacts", []):
                artifact_path = (root / artifact.get("path", "")).resolve()
                if root.resolve() not in artifact_path.parents:
                    errors.append(f"Experiment {experiment_id} artifact escapes repository.")
                elif not artifact_path.is_file():
                    errors.append(f"Experiment {experiment_id} artifact is missing: {artifact.get('path')}")
                elif sha256(artifact_path) != artifact.get("sha256"):
                    errors.append(f"Experiment {experiment_id} artifact checksum mismatch: {artifact.get('path')}")

    if len(experiment_ids) != len(set(experiment_ids)):
        errors.append("Experiment IDs must be unique in the final-record ledger.")
    if experiment_ids:
        last_id = experiment_ids[-1]
        if state.get("integrity", {}).get("last_experiment_id") != last_id:
            errors.append("STATE.json last_experiment_id does not match ledger tail.")

    known_ids = set(experiment_ids)
    preregistration_ids = {
        record.get("experiment_id") for record in preregistrations if record
    }
    active = state.get("objective", {}).get("active_experiment_id")
    if active is not None and active not in known_ids | preregistration_ids:
        errors.append("objective.active_experiment_id does not reference the ledger or a preregistration.")
    for preregistration in preregistrations:
        if preregistration.get("experiment_id") in known_ids:
            continue
        if (
            preregistration.get("design", {}).get("system_generation")
            != core_manifest.get("system_generation")
        ):
            errors.append(
                f"Pending experiment {preregistration.get('experiment_id')} does not use the current system generation."
            )
        if (
            active_evaluator_id is not None
            and preregistration.get("design", {}).get("evaluator_id")
            != active_evaluator_id
        ):
            errors.append(
                f"Pending experiment {preregistration.get('experiment_id')} does not use the current sealed evaluator."
            )
    baseline = state.get("objective", {}).get("baseline_experiment_id")
    if baseline is not None and baseline not in known_ids:
        errors.append("objective.baseline_experiment_id does not reference the ledger.")

    if state.get("data", {}).get("integrity_status") != manifest.get("integrity_status"):
        errors.append("STATE.json and DATA_MANIFEST.json integrity status disagree.")
    if manifest.get("integrity_status") == "validated" and not manifest.get("datasets"):
        errors.append("A validated manifest must contain at least one dataset.")

    all_trials = {}
    for record in records + preregistrations:
        experiment_id = record.get("experiment_id")
        if experiment_id:
            all_trials[experiment_id] = record
    maximum_trial = max(
        (record.get("design", {}).get("trial_number", 0) for record in all_trials.values()),
        default=0,
    )
    if budget.get("trials_consumed") != maximum_trial:
        errors.append("trials_consumed does not match allocated experiment trials.")
    holdout_count = sum(
        1 for record in all_trials.values() if record.get("design", {}).get("holdout_access") is True
    )
    if budget.get("holdout_touches") != holdout_count:
        errors.append("holdout_touches does not match allocated holdout experiments.")

    found_skills = set()
    for skill_file in sorted((root / "skills").glob("*/SKILL.md")):
        folder_name = skill_file.parent.name
        frontmatter = parse_skill_frontmatter(skill_file, errors)
        if frontmatter.get("name") != folder_name:
            errors.append(f"{skill_file}: skill name must match directory.")
        found_skills.add(folder_name)
    missing_skills = CORE_SKILLS - found_skills
    if missing_skills:
        errors.append(f"Missing immutable core skills: {sorted(missing_skills)}")
    declared_skills = {
        item.get("name") for item in core_manifest.get("core_skills", [])
    }
    if declared_skills != CORE_SKILLS:
        errors.append("CORE_MANIFEST.json core skill set disagrees with validator.")
    declared_versions = {
        item.get("name"): item.get("version")
        for item in core_manifest.get("core_skills", [])
    }
    for skill_file in sorted((root / "skills").glob("*/SKILL.md")):
        frontmatter = parse_skill_frontmatter(skill_file, errors)
        skill_name = skill_file.parent.name
        if declared_versions.get(skill_name) != frontmatter.get("version"):
            errors.append(f"{skill_name}: version disagrees with CORE_MANIFEST.json.")
    for relative in core_manifest.get("protected_files", []):
        if not (root / relative).is_file():
            errors.append(f"Protected file does not exist: {relative}")
    for component in core_manifest.get("sealed_components", []):
        for entry in component.get("paths", []):
            relative = entry["path"] if isinstance(entry, dict) else entry
            if not (root / relative).is_file():
                errors.append(f"Sealed component path does not exist: {relative}")
            elif isinstance(entry, dict) and sha256(root / relative) != entry.get("sha256"):
                errors.append(f"Sealed component checksum mismatch: {relative}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Alpha Lab repository contract: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
