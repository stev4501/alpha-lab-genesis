#!/usr/bin/env python3
"""Register or resolve an immutable market-data snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_adapters.immutable_snapshots import (  # noqa: E402
    register_snapshot,
    resolve_as_of,
    validate_registry,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register")
    register.add_argument("--source", required=True)
    register.add_argument("--dataset-id", required=True)
    register.add_argument("--series-id", required=True)
    register.add_argument("--as-of", required=True)
    register.add_argument("--retrieved-at", required=True)

    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("--series-id", required=True)
    resolve.add_argument("--as-of", required=True)

    subparsers.add_parser("validate")
    args = parser.parse_args()

    if args.command == "register":
        record = register_snapshot(
            ROOT,
            (ROOT / args.source),
            args.dataset_id,
            args.series_id,
            args.as_of,
            args.retrieved_at,
        )
        print(json.dumps(record, sort_keys=True))
        return 0
    if args.command == "resolve":
        print(
            json.dumps(
                resolve_as_of(ROOT, args.series_id, args.as_of), sort_keys=True
            )
        )
        return 0
    errors = validate_registry(ROOT)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Immutable snapshot registry: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
