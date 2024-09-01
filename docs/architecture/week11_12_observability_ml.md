# DriveCore Week 11-12 Observability + ML Export

## Goal

Close the loop from telemetry processing to operational monitoring and training data generation.

## Implemented Components

1. **Observability monitor**
   - Aggregates metrics from queue, stream, DLQ, and indexed storage
   - Computes drop ratio and queue backlog
   - Emits alert conditions:
     - high drop ratio
     - high queue backlog
     - indexer lag (processed > indexed)
2. **ML dataset export**
   - Exports filtered event sets from SQLite into JSONL
   - Writes manifest with filter params, count, and source metadata
   - Available through:
     - CLI: `python -m ml.exporter.main`
     - API: `POST /datasets/export`

## Why this matters for autonomy telemetry

- Observability ensures failures are visible before data quality degrades.
- Export tooling provides direct pipelines for model training data curation.
- Together, this creates a practical car-to-cloud-to-ML feedback loop.
