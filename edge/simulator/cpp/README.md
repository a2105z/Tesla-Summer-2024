# C++ Edge Telemetry Agent

## Build

```bash
cmake -S . -B build
cmake --build build
```

## Run

```bash
./build/drivecore_sim --steps 120 --seed 7 --vehicle-id vehicle_sim_001
```

## Output

- stdout: batched payload envelopes with NDJSON payload
- stderr: telemetry reliability metrics

## Week 3-4 Features

- Trigger context capture (`--pre-context`, `--post-context`)
- Batch flush controls (`--batch-size`, `--flush-interval`)
- Retry logic with exponential backoff parameters
- Configurable transport failure simulation (`--transport-fail-rate`)

## Note

Python transport uses production-style `gzip` compression.  
C++ currently emits uncompressed NDJSON payloads (`compression=none`) to keep the build dependency-free for local development.
