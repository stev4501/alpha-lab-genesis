#!/usr/bin/env python3
"""Start a bounded Alpha Lab run with an atomic STATE.json update."""

import argparse
import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def start_run(root: Path, minutes: int, max_experiments: int) -> dict:
    state_path = root / "STATE.json"
    with state_path.open(encoding="utf-8") as handle:
        state = json.load(handle)

    reserve = state["run"]["reserve_minutes"]
    if minutes <= reserve:
        raise ValueError(
            f"Session budget must exceed the {reserve}-minute closing reserve."
        )
    if max_experiments < 1:
        raise ValueError("max_experiments must be at least 1.")
    if state["run"]["status"] in {"orienting", "executing", "closing"}:
        raise ValueError("An active run already exists; recover or close it first.")

    now = datetime.now(timezone.utc)
    run_id = f"R-{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
    previous = state["run"]["run_id"]

    state["revision"] += 1
    state["updated_at"] = now.isoformat().replace("+00:00", "Z")
    state["run"].update(
        {
            "run_id": run_id,
            "previous_run_id": previous,
            "status": "orienting",
            "started_at": now.isoformat().replace("+00:00", "Z"),
            "deadline_at": (now + timedelta(minutes=minutes))
            .isoformat()
            .replace("+00:00", "Z"),
            "dirty_shutdown": True,
        }
    )
    state["budget"].update(
        {
            "session_minutes": minutes,
            "used_minutes": 0,
            "max_experiments": max_experiments,
            "experiments_completed": 0,
        }
    )
    state["integrity"]["validation_status"] = "pending"
    atomic_write_json(state_path, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, required=True)
    parser.add_argument("--max-experiments", type=int, default=1)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()

    state = start_run(args.root.resolve(), args.minutes, args.max_experiments)
    print(
        json.dumps(
            {
                "run_id": state["run"]["run_id"],
                "deadline_at": state["run"]["deadline_at"],
                "closing_reserve_minutes": state["run"]["reserve_minutes"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
