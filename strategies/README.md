# Strategies

Each strategy receives a stable directory such as `S-0001/` containing:

- `strategy.json`: immutable identity and current version pointer
- `SPEC.md`: signal, universe, timing, sizing, and risk rules
- `src/`: executable implementation
- `tests/`: software and invariant tests
- `CHANGELOG.md`: append-only strategy evolution

Do not store experiment results here. Results belong under `results/<experiment_id>/`.
