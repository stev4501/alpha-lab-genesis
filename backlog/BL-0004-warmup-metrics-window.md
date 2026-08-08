# BL-0004: Document warm-up handling in the metrics window

- Status: open
- Priority: 4
- Requires sealed changes: no (documentation only)
- Origin: ADR-0008 proof backlog (2026-08-08)

## The observation

`evaluator/daily_bar.py` (sealed — read, never modify) slices the equity
series at `evaluation_rows = equity_rows[warmup_sessions:]` (line 424) and
then, inside `calculate_metrics` (line 216), computes the first entry of the
daily-return series as `equities[0] / initial_capital - 1`. That first
"daily" return is therefore measured from the capital at session 0, across
the entire warm-up span, into the close of the first post-warm-up session —
compressed into a single daily observation.

With `warmup_sessions = 1` (the only value used so far — E-0002 preregisters
`parameter_coordinates.warmup_sessions = 1`, and fills are suppressed during
warm-up so equity stays flat at initial capital), the numerical effect is
nil. The task is to document precisely what happens at warm-up values
greater than one, where the same construction makes the first observation
span multiple sessions.

## Deliverable

A short analysis note (suggested: `docs/warmup-metrics-note.md`) that:

1. Traces the exact code path: warm-up fill suppression
   (`if index + 1 >= warmup_sessions`, line 416), the evaluation slice
   (line 424), the first-return construction (line 216), and the
   benchmark interval start (`dates[warmup_sessions]`, line 271).
2. States the practical effect for `warmup_sessions > 1`: the first element
   of the daily-return series aggregates the full warm-up-to-first-
   evaluation-close span as one observation, and `len(daily_returns)` (used
   in the annualization exponent, line 223, and in volatility/Sharpe, lines
   227–236) counts evaluation sessions only — quantify how this would bias
   annualized return, volatility, and Sharpe for a worked example (a small
   synthetic series is fine, computed in the note by hand or in a scratch
   script — never by adding code to the evaluator).
3. States clearly whether any existing recorded metric (E-0001, E-0002) is
   affected. Expected answer: no, because both used warmup_sessions = 1 and
   equity is provably flat during warm-up; show the reasoning.
4. If the analysis concludes the behavior is a real defect for future
   multi-session warm-ups, add that finding as an input to the G-0004
   change request scope (BL-0002) rather than proposing an in-generation
   patch.

## Definition of done

The note exists, is linked from the journal and HANDOFF.md, and no evaluator
bytes, manifest hashes, or recorded metrics changed.
