# DriveCore ML Export (Week 11-12)

Exports filtered telemetry slices into training-ready JSONL datasets.

## Run CLI export

```bash
python -m ml.exporter.main --event-type hard_brake --min-speed 20 --limit 1000
```

## Output

- Dataset JSONL: `ml/exports/dataset_<timestamp>.jsonl`
- Manifest JSON: `ml/exports/dataset_<timestamp>.manifest.json`

This mirrors autonomy workflows where edge-case telemetry is materialized into training datasets.
