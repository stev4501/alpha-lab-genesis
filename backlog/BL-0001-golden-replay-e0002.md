# BL-0001: Formalize a golden replay of E-0002

- Status: open
- Priority: 1
- Requires sealed changes: no
- Origin: ADR-0008 proof backlog (2026-08-08)

## Goal

A repeatable check that re-running the sealed evaluator with E-0002's exact
inputs reproduces E-0002's metrics bit-identically. This turns the loop's
central determinism claim — same manifest, same snapshot, same strategy, same
metrics — into an asserted fact instead of an assumption.

## Exact inputs (all already in the repository)

- Preregistration: `results/E-0002/preregistration.json`
- Evaluator: `evaluator/daily_bar.py` (sealed, component EV-0002)
- Strategy: `strategies/S-0002/strategy.py`, sha256
  `e28f6de15b2345d4311a17ea20671c77233b94b5538e50b8825f51a6860c3b5c`
- Data manifest: `DATA_MANIFEST.json` at manifest_version 1.0.0, design
  records `data_manifest_sha256`
  `74f2d455abde729d127af73a36f307f3352e0859371117520697b60b68c1b39e`
  (note: the manifest has since moved to 1.2.0 — the replay must confirm the
  evaluator consumes only the D-0001 dataset entry, whose snapshot bytes are
  unchanged, and record how the manifest-hash difference is handled)
- Dataset: D-0001, snapshot
  `data/snapshots/D-0001/225556599a155026d0032b428d3db60b59ee875c41581c9bf1bc7019a1d2ea30.csv`
- Expected output: `results/E-0002/metrics.json` (baseline sha256
  `17ba4a0d72b1022e402adc51d35f53222e90473921cac2f3c27fcf2d9450b88e`)

## Deliverable

A pytest test (suggested: `tests/test_golden_replay_e0002.py`) that runs the
evaluator's evaluation path against the inputs above, writing any output to a
temporary directory — NEVER into `results/E-0002/` — and asserts the produced
metrics JSON is byte-identical (or, if ordering makes byte-identity
unachievable, key-by-key exactly equal with an explanation in the journal) to
`results/E-0002/metrics.json`. The test must not modify any existing file
under `results/` and must not require network access.

## Notes for the acting agent

- Read `evaluator/daily_bar.py`'s `__main__` entry to learn its CLI/contract
  before writing anything; do not re-implement metric math yourself.
- If the evaluator cannot be pointed at a scratch output directory without
  modifying it, that is a blocker: record it in the journal and in this file,
  and draft the needed interface change into `core_change_requests/` instead
  of patching the sealed file.
