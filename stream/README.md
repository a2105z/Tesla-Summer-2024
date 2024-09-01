# DriveCore Stream Processing (Week 7-8)

Simple and reliable stream pipeline built on top of ingestion queue output.

## What it does

- Reads new batch lines from `ingestion/data/queue.ndjson`
- Validates each event
- Runs multimodal autonomy annotation:
  - synthetic vision embedding from frame IDs
  - optional operator command signal
  - fused risk score, decision label, anomaly reasons
- Enriches valid events (weather + processing metadata + autonomy block)
- Routes valid events to `stream/data/processed_events.ndjson`
- Routes invalid events to `stream/data/dlq.ndjson`
- Tracks progress with an offset checkpoint

## Run

```bash
python -m stream.processor.main run-once
```

Replay DLQ events after fixes:

```bash
python -m stream.processor.main replay-dlq
```

Run multimodal latency/throughput benchmark:

```bash
python -m stream.processor.benchmark --events 10000 --warmup 500 --seed 7
```

Benchmark output includes:

- throughput (`events/sec`)
- latency percentiles (`min`, `p50`, `p95`, `p99`, `max`) in microseconds

## Environment Variables

- `DRIVECORE_QUEUE_PATH`
- `DRIVECORE_PROCESSED_EVENTS_PATH`
- `DRIVECORE_DLQ_PATH`
- `DRIVECORE_STREAM_OFFSET_PATH`
