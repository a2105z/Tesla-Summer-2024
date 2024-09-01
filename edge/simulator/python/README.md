# Python Edge Telemetry Agent

## Run

```bash
python main.py --steps 120 --seed 7 --vehicle-id vehicle_sim_001
```

## Output

- stdout: transmission batches (`ndjson` payloads compressed with `gzip` and base64-encoded)
- stderr: pipeline metrics summary

## Week 3-4 Features

- Ring buffer context capture (`--pre-context`)
- Post-trigger context capture (`--post-context`)
- Batch packaging (`--batch-size`, `--flush-interval`)
- Compression (`gzip`)
- Retry queue with exponential backoff and jitter
- Configurable transport failure simulation (`--transport-fail-rate`)

## Useful Commands

Only metrics:

```bash
python main.py --steps 200 --quiet
```

Stress retries:

```bash
python main.py --steps 200 --transport-fail-rate 0.55 --batch-size 6
```
