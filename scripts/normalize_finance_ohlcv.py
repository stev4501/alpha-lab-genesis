#!/usr/bin/env python3
"""Normalize connector OHLCV CSV bytes into the sealed evaluator format."""

from __future__ import annotations

import argparse
from pathlib import Path


RAW_HEADER = b"date,open,high,low,close,volume"
OUTPUT_HEADER = b"date,symbol,open,high,low,close,volume\n"


def normalize(source: Path, destination: Path, symbol: str) -> None:
    lines = source.read_bytes().splitlines(keepends=True)
    if not lines or lines[0].rstrip(b"\r\n") != RAW_HEADER:
        raise ValueError("Unexpected finance OHLCV header.")
    symbol_bytes = symbol.encode("ascii")
    output = bytearray(OUTPUT_HEADER)
    for line_number, line in enumerate(lines[1:], start=2):
        ending = b"\r\n" if line.endswith(b"\r\n") else b"\n"
        body = line.rstrip(b"\r\n")
        if body.count(b",") != 5:
            raise ValueError(f"Unexpected column count on line {line_number}.")
        date, remainder = body.split(b",", 1)
        output.extend(date + b"," + symbol_bytes + b"," + remainder + ending)
    destination.write_bytes(bytes(output))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    normalize(args.source, args.destination, args.symbol)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
