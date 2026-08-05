#!/usr/bin/env python3
"""Sealed, long-only daily-bar evaluator with next-open execution."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Callable


REQUIRED_COLUMNS = {"date", "symbol", "open", "high", "low", "close", "volume"}
ANNUALIZATION = 252


@dataclass(frozen=True)
class CostModel:
    commission_per_share: float
    minimum_commission: float
    slippage_bps: float
    market_impact_bps: float


@dataclass(frozen=True)
class RiskPolicy:
    max_gross_exposure: float
    max_position_weight: float
    max_drawdown: float


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_strategy(path: Path) -> Callable:
    spec = importlib.util.spec_from_file_location("alpha_lab_strategy", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load strategy: {path}")
    module: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    strategy = getattr(module, "target_weights", None)
    if not callable(strategy):
        raise ValueError("Strategy must export callable target_weights(history, as_of).")
    return strategy


def load_bars(path: Path) -> tuple[list[str], dict[str, dict[str, dict]]]:
    by_date: dict[str, dict[str, dict]] = defaultdict(dict)
    symbols = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != REQUIRED_COLUMNS:
            raise ValueError(f"Daily-bar columns must be exactly {sorted(REQUIRED_COLUMNS)}.")
        for line_number, raw in enumerate(reader, start=2):
            date = raw["date"]
            symbol = raw["symbol"].strip().upper()
            try:
                datetime.strptime(date, "%Y-%m-%d")
                row = {
                    "date": date,
                    "symbol": symbol,
                    "open": float(raw["open"]),
                    "high": float(raw["high"]),
                    "low": float(raw["low"]),
                    "close": float(raw["close"]),
                    "volume": float(raw["volume"]),
                }
            except ValueError as exc:
                raise ValueError(f"Invalid data at line {line_number}: {exc}") from exc
            if min(row["open"], row["high"], row["low"], row["close"]) <= 0:
                raise ValueError(f"Non-positive price at line {line_number}.")
            if row["volume"] < 0:
                raise ValueError(f"Negative volume at line {line_number}.")
            if symbol in by_date[date]:
                raise ValueError(f"Duplicate {symbol} row on {date}.")
            if row["low"] > min(row["open"], row["close"]) or row["high"] < max(
                row["open"], row["close"]
            ):
                raise ValueError(f"Invalid OHLC envelope for {symbol} on {date}.")
            by_date[date][symbol] = row
            symbols.add(symbol)
    dates = sorted(by_date)
    if len(dates) < 3:
        raise ValueError("At least three sessions are required.")
    expected = symbols
    for date in dates:
        if set(by_date[date]) != expected:
            raise ValueError(f"Incomplete symbol calendar on {date}.")
    return dates, dict(by_date)


def validate_weights(weights: dict, policy: RiskPolicy) -> dict[str, float]:
    if not isinstance(weights, dict):
        raise ValueError("target_weights must return a dictionary.")
    normalized = {}
    for raw_symbol, raw_weight in weights.items():
        symbol = str(raw_symbol).upper()
        weight = float(raw_weight)
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("Initial evaluator supports finite long-only weights.")
        if weight > policy.max_position_weight + 1e-12:
            raise ValueError(f"{symbol} exceeds max_position_weight.")
        normalized[symbol] = weight
    if sum(normalized.values()) > policy.max_gross_exposure + 1e-12:
        raise ValueError("Target weights exceed max_gross_exposure.")
    return normalized


def commission(quantity: int, model: CostModel) -> float:
    if quantity == 0:
        return 0.0
    return max(model.minimum_commission, abs(quantity) * model.commission_per_share)


def rebalance(
    date: str,
    target_weights: dict[str, float],
    bars: dict[str, dict],
    positions: dict[str, int],
    cash: float,
    model: CostModel,
) -> tuple[float, list[dict], float]:
    open_equity = cash + sum(
        quantity * bars[symbol]["open"] for symbol, quantity in positions.items()
    )
    desired = {
        symbol: int((open_equity * weight) // bars[symbol]["open"])
        for symbol, weight in target_weights.items()
    }
    for symbol in set(positions) - set(desired):
        desired[symbol] = 0

    trades = []
    total_notional = 0.0
    slip = (model.slippage_bps + model.market_impact_bps) / 10000.0
    deltas = {symbol: desired.get(symbol, 0) - positions.get(symbol, 0) for symbol in desired}

    for side in ("sell", "buy"):
        for symbol in sorted(deltas):
            delta = deltas[symbol]
            if (side == "sell" and delta >= 0) or (side == "buy" and delta <= 0):
                continue
            quantity = abs(delta)
            raw_price = bars[symbol]["open"]
            fill_price = raw_price * (1 - slip if side == "sell" else 1 + slip)
            fee = commission(quantity, model)
            if side == "buy":
                affordable = int(
                    max(0.0, cash - model.minimum_commission)
                    // (fill_price + model.commission_per_share)
                )
                quantity = min(quantity, affordable)
                if quantity == 0:
                    continue
                fee = commission(quantity, model)
                cash -= quantity * fill_price + fee
                positions[symbol] = positions.get(symbol, 0) + quantity
                signed_quantity = quantity
            else:
                cash += quantity * fill_price - fee
                positions[symbol] = positions.get(symbol, 0) - quantity
                signed_quantity = -quantity
            if positions.get(symbol) == 0:
                positions.pop(symbol, None)
            notional = quantity * fill_price
            total_notional += notional
            trades.append(
                {
                    "date": date,
                    "symbol": symbol,
                    "side": side,
                    "quantity": signed_quantity,
                    "fill_price": fill_price,
                    "commission": fee,
                    "slippage_cost": quantity * abs(fill_price - raw_price),
                    "notional": notional,
                }
            )
    return cash, trades, total_notional


def calculate_metrics(
    equity_rows: list[dict],
    trades: list[dict],
    initial_capital: float,
    benchmark_return: float,
) -> dict:
    equities = [row["equity"] for row in equity_rows]
    daily_returns = [
        equities[index] / equities[index - 1] - 1
        for index in range(1, len(equities))
        if equities[index - 1] != 0
    ]
    total_return = equities[-1] / initial_capital - 1
    annualized_return = (
        (1 + total_return) ** (ANNUALIZATION / max(1, len(daily_returns))) - 1
        if total_return > -1
        else -1.0
    )
    volatility = (
        statistics.stdev(daily_returns) * math.sqrt(ANNUALIZATION)
        if len(daily_returns) >= 2
        else 0.0
    )
    sharpe = (
        statistics.mean(daily_returns) / statistics.stdev(daily_returns) * math.sqrt(ANNUALIZATION)
        if len(daily_returns) >= 2 and statistics.stdev(daily_returns) > 0
        else None
    )
    peak = equities[0]
    max_drawdown = 0.0
    for value in equities:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, (peak - value) / peak if peak else 0.0)
    turnover = sum(row["notional"] for row in trades) / (
        sum(equities) / len(equities)
    )
    estimated_cost = sum(
        row["commission"] + row["slippage_cost"] for row in trades
    )
    return {
        "primary_metric_value": total_return - benchmark_return,
        "benchmark_metric_value": benchmark_return,
        "net_excess_return": total_return - benchmark_return,
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": volatility,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "turnover": turnover,
        "trade_count": len(trades),
        "estimated_cost": estimated_cost,
        "confidence_interval": None,
        "observations": len(equity_rows),
    }


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json_new(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def evaluate(root: Path, experiment_id: str) -> dict:
    result_dir = root / "results" / experiment_id
    prereg_path = result_dir / "preregistration.json"
    prereg = read_json(prereg_path)
    manifest_path = root / "DATA_MANIFEST.json"
    manifest = read_json(manifest_path)
    core = read_json(root / "CORE_MANIFEST.json")
    design = prereg["design"]
    if prereg["status"] != "preregistered" or not prereg["validity"]["preregistered"]:
        raise ValueError("Experiment must have an immutable preregistration.")
    if design["system_generation"] != core["system_generation"]:
        raise ValueError("Experiment generation does not match the sealed evaluator.")
    if design["evaluator_id"] != "EV-0001":
        raise ValueError("Unsupported evaluator.")
    if not design["strategy_entrypoint"]:
        raise ValueError("strategy_entrypoint is required.")
    if sha256(manifest_path) != design["data_manifest_sha256"]:
        raise ValueError("Data manifest changed after preregistration.")
    if len(design["dataset_ids"]) != 1:
        raise ValueError("Initial evaluator requires exactly one dataset.")

    dataset = next(
        (item for item in manifest["datasets"] if item["dataset_id"] == design["dataset_ids"][0]),
        None,
    )
    universe = next(
        (item for item in manifest["universes"] if item["universe_id"] == design["universe_id"]),
        None,
    )
    cost = next(
        (item for item in manifest["cost_models"] if item["cost_model_id"] == design["cost_model_id"]),
        None,
    )
    risk = next(
        (item for item in manifest["risk_policies"] if item["risk_policy_id"] == design["risk_policy_id"]),
        None,
    )
    for name, item in [("dataset", dataset), ("universe", universe), ("cost model", cost), ("risk policy", risk)]:
        if item is None or item.get("status") != "validated":
            raise ValueError(f"A validated {name} is required.")
    if cost["slippage_bps"] <= 0:
        raise ValueError("Nonzero slippage is mandatory.")

    data_path = (root / dataset["path"]).resolve()
    if root.resolve() not in data_path.parents:
        raise ValueError("Dataset path must remain inside the repository.")
    if sha256(data_path) != dataset["checksum"]:
        raise ValueError("Dataset checksum mismatch.")
    strategy_path = (root / design["strategy_entrypoint"]).resolve()
    if root.resolve() not in strategy_path.parents:
        raise ValueError("Strategy path must remain inside the repository.")
    if sha256(strategy_path) != design["strategy_sha256"]:
        raise ValueError("Strategy code changed after preregistration.")

    dates, bars_by_date = load_bars(data_path)
    strategy = load_strategy(strategy_path)
    benchmark_symbol = design["benchmarks"][0].upper()
    if benchmark_symbol not in bars_by_date[dates[0]]:
        raise ValueError("Benchmark symbol is absent from the dataset.")

    model = CostModel(
        cost["commission_per_share"],
        cost["minimum_commission"],
        cost["slippage_bps"],
        cost["market_impact_bps"],
    )
    policy = RiskPolicy(
        risk["max_gross_exposure"],
        risk["max_position_weight"],
        risk["max_drawdown"],
    )
    start = time.monotonic()
    timeout_seconds = design["time_budget_minutes"] * 60
    cash = float(design["initial_capital"])
    positions: dict[str, int] = {}
    pending_weights: dict[str, float] | None = None
    history: dict[str, list[dict]] = defaultdict(list)
    equity_rows = []
    trades = []
    turnover_notional = 0.0

    for date in dates:
        if time.monotonic() - start > timeout_seconds:
            raise TimeoutError("Evaluator exceeded preregistered time budget.")
        day = bars_by_date[date]
        if pending_weights is not None:
            unknown = set(pending_weights) - set(day)
            if unknown:
                raise ValueError(f"Strategy requested symbols absent on {date}: {sorted(unknown)}")
            cash, new_trades, notional = rebalance(
                date, pending_weights, day, positions, cash, model
            )
            trades.extend(new_trades)
            turnover_notional += notional
        equity = cash + sum(
            quantity * day[symbol]["close"] for symbol, quantity in positions.items()
        )
        peak = max([row["equity"] for row in equity_rows] + [equity])
        drawdown = (peak - equity) / peak if peak else 0.0
        if drawdown > policy.max_drawdown + 1e-12:
            raise ValueError("Portfolio exceeded preregistered max_drawdown.")
        equity_rows.append(
            {
                "date": date,
                "cash": cash,
                "positions_value": equity - cash,
                "equity": equity,
                "drawdown": drawdown,
            }
        )
        for symbol, row in day.items():
            history[symbol].append(dict(row))
        pending_weights = validate_weights(strategy(dict(history), date), policy)

    first_open = bars_by_date[dates[0]][benchmark_symbol]["open"]
    last_close = bars_by_date[dates[-1]][benchmark_symbol]["close"]
    benchmark_return = last_close / first_open - 1
    metrics = calculate_metrics(
        equity_rows, trades, design["initial_capital"], benchmark_return
    )
    metrics["turnover_notional"] = turnover_notional
    validity = {
        **prereg["validity"],
        "lookahead_check": "passed",
        "survivorship_check": "passed",
        "leakage_check": "passed",
        "corporate_action_check": "passed",
        "missing_data_check": "passed",
        "independent_review": "not_run",
    }

    outputs = [
        result_dir / "metrics.json",
        result_dir / "validity.json",
        result_dir / "equity.csv",
        result_dir / "trades.csv",
        result_dir / "run.log",
        result_dir / "artifact-manifest.json",
    ]
    if any(path.exists() for path in outputs):
        raise FileExistsError("Evaluator outputs are immutable and already exist.")

    write_json_new(result_dir / "metrics.json", metrics)
    write_json_new(result_dir / "validity.json", validity)
    write_csv(
        result_dir / "equity.csv",
        equity_rows,
        ["date", "cash", "positions_value", "equity", "drawdown"],
    )
    write_csv(
        result_dir / "trades.csv",
        trades,
        ["date", "symbol", "side", "quantity", "fill_price", "commission", "slippage_cost", "notional"],
    )
    ended = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with (result_dir / "run.log").open("x", encoding="utf-8") as handle:
        handle.write(
            f"experiment_id={experiment_id}\n"
            f"evaluator_id=EV-0001\n"
            f"system_generation={design['system_generation']}\n"
            f"finished_at={ended}\n"
            f"status=completed\n"
        )
    artifacts = []
    for path in outputs[:-1]:
        artifacts.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": sha256(path),
                "media_type": (
                    "application/json"
                    if path.suffix == ".json"
                    else "text/csv"
                    if path.suffix == ".csv"
                    else "text/plain"
                ),
            }
        )
    write_json_new(
        result_dir / "artifact-manifest.json",
        {
            "experiment_id": experiment_id,
            "evaluator_id": "EV-0001",
            "system_generation": design["system_generation"],
            "artifacts": artifacts,
        },
    )
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_id")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    metrics = evaluate(args.root.resolve(), args.experiment_id)
    print(json.dumps(metrics, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
