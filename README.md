# Alpha Lab Genesis

A Day 1 filesystem for an autonomous, paper-only stock-strategy research agent.
The objective is not to prove guaranteed profits. It is to accumulate
reproducible, falsifiable evidence of risk-adjusted excess returns after costs.

## Start Here

Every fresh agent reads these files in order:

1. `MISSION.md`
2. `CONTEXT.md`
3. `STATE.json`
4. `DATA_MANIFEST.json`
5. the tail of `EXPERIMENTS.jsonl`
6. `HYPOTHESES.md`, `DECISIONS.md`, and `FAILURES.md`
7. the core skills relevant to the next action

Then it runs:

```bash
python scripts/validate_repository.py
python scripts/bootstrap_run.py --minutes 120
```

## Filesystem Contract

```text
alpha-lab-genesis/
├── MISSION.md                  immutable objective and safety boundary
├── CONTEXT.md                  canonical vocabulary
├── STATE.json                  current materialized operating state
├── EXPERIMENTS.jsonl           append-only experiment ledger
├── HYPOTHESES.md               active and rejected hypotheses
├── DECISIONS.md                append-only architectural decisions index
├── FAILURES.md                 failure patterns and unresolved blockers
├── DATA_MANIFEST.json          data provenance and integrity status
├── CORE_MANIFEST.json          immutable core and generation boundary
├── schemas/
│   ├── state.schema.json
│   ├── experiment.schema.json
│   └── data-manifest.schema.json
├── docs/adr/                   append-only design decisions
├── strategies/                 versioned strategy definitions
├── results/                    immutable experiment artifacts
├── logs/                       run and tool logs
├── skills/                     core and agent-created skills
├── scripts/                    deterministic state-management utilities
├── dev/plugins/                vendored developer-only skill plugins
└── tests/                      repository contract tests
```

Third-party skills under `dev/plugins/` are for development, not for the
autonomous loop. The sole supported delivery route is the dedicated **Alpha Lab
Dev** cloud environment documented in `docs/cloud-environment-dev-skills.md`.
Its setup installs the pinned plugin and a user-level pointer to the repository
configuration. The loop's runner strips skills outright
(`--disable-slash-commands`, `--disallowedTools "Skill"`) and does not run in
that environment.

The cloud setup is intentionally not a repository plugin declaration.

## Source-of-Truth Rules

- `EXPERIMENTS.jsonl` is append-only and authoritative for experiment history.
- `STATE.json` is replaceable and must be reconstructable from durable artifacts.
- `DATA_MANIFEST.json` is authoritative for dataset identity and provenance.
- `CORE_MANIFEST.json` defines protected files, core skills, and the current
  research-system generation.
- Failed and discarded experiments are retained.
- Results never overwrite prior results.
- Skills guide decisions; scripts enforce deterministic invariants.
- No artifact may imply that future profitability is proven.

See `docs/capability-map.md` for the owner, inputs, outputs, and blocking
conditions of every required capability.

See `docs/tooling-recommendations.md` for the recommended dependency sequence
and `docs/source-evaluation.md` for the full source-linked project comparison.

## Validation

```bash
python -m unittest discover -s tests -v
python scripts/validate_repository.py
```

The standard library is sufficient for the initial skeleton.

## EV-0002 Experiment Pipeline

After validating data, universe, cost, and risk records:

```bash
python scripts/preregister_experiment.py \
  --hypothesis H-0001 \
  --strategy S-0002 \
  --strategy-entrypoint strategies/S-0002/strategy.py \
  --title "Passive SPY baseline" \
  --rationale "Validate evaluator timing and accounting." \
  --prediction "The first fill occurs at the next session open." \
  --dataset D-0001 \
  --universe U-0001 \
  --cost-model C-0001 \
  --risk-policy R-0001 \
  --criterion "Artifacts reconcile and validation passes."

python evaluator/daily_bar.py E-0002

# A different agent records the evidence review.
python scripts/record_evidence_review.py E-0002 \
  --reviewer independent-reviewer \
  --decision keep \
  --finding "Timing and accounting match EV-0002." \
  --next-action "Add a strategy-specific null baseline."

python scripts/finalize_experiment.py E-0002 \
  --outcome keep \
  --reason "Baseline evaluator contract passed." \
  --next-action "Add a strategy-specific null baseline." \
  --next-stage baseline

python scripts/validate_repository.py
```

See `docs/evaluator-contract.md` for the clock, strategy interface, limitations,
immutable outputs, and promotion requirements.
