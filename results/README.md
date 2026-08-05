# Results

Create one immutable directory per experiment:

```text
results/E-0001/
├── metrics.json
├── equity.csv
├── trades.csv
├── validity.json
├── run.log
└── artifact-manifest.json
```

Never overwrite a completed result directory. A rerun receives a new experiment ID.
