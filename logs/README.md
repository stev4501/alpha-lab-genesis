# Logs

This directory holds runner transcripts, not experiment evidence.

`loop/run_session.sh` writes `logs/loop/` — `runner.log`, `selfcheck.log`,
`validate.log`, and `agent_result.json` — for each session. That path is
gitignored so the runner's `git add -A` does not commit a session's own
transcript into that session's commit. The transcripts are still captured:
`.github/workflows/session.yml` uploads `logs/loop/` as a workflow artifact with
30-day retention, and the salvage path copies the first failing check into
`HANDOFF.md`.

Per-experiment execution logs are **not** here. They live inside the immutable
result directory as `results/<E-XXXX>/run.log`, checksummed by that experiment's
`artifact-manifest.json` alongside the metrics, equity, trades, and validity
files. That keeps the log under the same never-overwritten guarantee as the rest
of the experiment's evidence, which a gitignored directory could not offer.

This file previously described a `logs/<run_id>/` convention that nothing has
ever written. Nothing was lost by correcting it — the convention was aspirational
and the evidence path was always `results/`.
