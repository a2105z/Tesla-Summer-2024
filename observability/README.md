# DriveCore Observability (Week 11-12)

Collects system health metrics from ingestion, stream, and storage outputs.

## Run

```bash
python -m observability.main
```

Write report to file:

```bash
python -m observability.main --write-report observability/reports/latest.json
```

## Report includes

- queue batch count
- stream backlog (queue minus consumer offset)
- processed and DLQ event counts
- indexed DB event count
- drop ratio
- alert list (drop ratio, backlog, index lag)
