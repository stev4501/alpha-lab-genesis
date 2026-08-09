# BL-0001: Formalize a golden replay of E-0002

- Status: DONE 2026-08-09 (session 2026-08-09-0525) — deliverable is
  `tests/test_golden_replay_e0002.py`, 11 tests / 17 subtests green, and the
  full suite plus `scripts/validate_repository.py` stay green. One substantive
  finding, recorded below; it is an input to BL-0002, not a reopening of this
  item.
- Priority: 1 (closed)
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

## Outcome 2026-08-09

No blocker. `evaluate(root, experiment_id)` already accepts a root, so the
replay builds a throwaway root under `tempfile` holding only the paths the
evaluator reads. Nothing under `results/` was written; the test itself
re-hashes every file in `results/E-0002/` before and after and asserts none
moved.

How the manifest-hash difference was handled (the open question in "Exact
inputs"): by pinning, not by relaxing. The evaluator refuses to run unless
`sha256(DATA_MANIFEST.json)` equals the preregistered
`data_manifest_sha256`, so the replay reads the 1.0.0 manifest bytes out of
git at `design.code_commit` (`5ff8f61`) and asserts their hash equals the
preregistered value first. That 1.0.0 manifest resolves D-0001 to
`data/SPY_2024-01-02_2025-12-31_1day.csv`, one of the duplicates the
2026-08-08 reduction deleted; its recorded checksum is exactly the name of the
surviving `data/snapshots/D-0001/2255565....csv`, so the replay copies those
bytes to the old path inside the scratch root and the evaluator re-hashes
them. `CORE_MANIFEST.json` is pinned the same way, because E-0002 ran under
G-0002 and the repository is at G-0003; the test additionally asserts that the
sealed sha256 recorded for `evaluator/daily_bar.py` at that commit equals the
sha256 of the evaluator on disk, which is what makes "the same evaluator" a
checked fact.

**Finding: bit-identity does not hold, and the reason is the interpreter.**
`validity.json`, `equity.csv`, and `trades.csv` replay byte-identically.
`metrics.json` does not: `turnover` replays as `0.8085773955620549` against
the recorded `0.8085773955620554`. Every other metric is exactly equal.
`turnover` is the only metric that divides by `sum()` over a 501-element float
list; CPython 3.12 changed `sum()` over floats to Neumaier compensated
summation (gh-100425). The test proves the mechanism rather than absorbing it
into a tolerance: it recomputes turnover from the byte-identical artifacts
with plain `sum()` and with `math.fsum()`, asserts the naive value equals this
run's own output, and asserts the recorded value equals one of the two. On the
loop runner (`.github/workflows/session.yml` pins python-version "3.11") the
recorded value is the compensated one, so E-0002 was originally produced on
CPython >= 3.12.

Consequence, for BL-0002 to weigh: `design.environment_id` is the free-text
string `"python-stdlib-mvp"` and nothing records or enforces an interpreter
version, so "same manifest, same snapshot, same strategy, same metrics" is
true only to ~1e-15 relative across interpreter versions, not bit-exactly.
Nothing about E-0002's recorded evidence is wrong; the determinism claim just
needs the interpreter named. Do not patch the sealed evaluator for this.
