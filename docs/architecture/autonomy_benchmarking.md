# DriveCore Multimodal Benchmarking

## Goal

Measure multimodal autonomy inference behavior under load, focusing on:

- per-event latency percentiles
- overall throughput (events/second)

## Benchmark scope

The benchmark uses synthetic events that include:

- telemetry state
- vision metadata (`frame_id`, lighting, scene hint)
- text command input (`operator_command`)

It runs the same autonomy annotation path used by stream enrichment:

- modality fusion
- decision inference
- anomaly detection

## CLI

```bash
python -m stream.processor.benchmark --events 10000 --warmup 500 --seed 7
```

## Output metrics

- `throughput_events_per_s`
- `latency_us_min`
- `latency_us_p50`
- `latency_us_p95`
- `latency_us_p99`
- `latency_us_max`

This gives a practical performance signal for internship demos and architecture discussions.
