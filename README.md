# DriveCore

DriveCore is an end-to-end autonomy telemetry pipeline that runs edge event detection, cloud ingestion, stream processing, storage indexing, query retrieval, observability checks, and ML dataset export.

## Multimodal Upgrade

DriveCore now includes a practical multimodal autonomy stage that combines:

- telemetry state features
- synthetic vision metadata and deterministic frame embeddings
- optional operator text commands

The stream layer fuses these signals into a risk score, predicts an autonomy action, and tags anomalies for downstream review/training.

## What The Codebase Does Right Now

1. **Edge simulation (Python + C++)**
   - Simulates vehicle state streams (`speed`, `brake`, `lane offset`, `obstacle distance`, `steering`).
   - Detects high-value events (`hard_brake`, `lane_departure`, `sudden_obstacle`).
   - Attaches multimodal metadata (`vision` hints + optional `operator_command`) to each event.
   - Captures context windows around events (pre/post ticks).
   - Batches events and applies retry logic.
   - Python edge path uses `gzip` payload compression; C++ edge path keeps payloads uncompressed for dependency-free local runs.

2. **Ingestion service (Python / FastAPI)**
   - Exposes `POST /ingest` and `GET /health`.
   - Validates auth bearer token.
   - Validates and decodes batch payloads.
   - Enforces idempotency with SQLite.
   - Publishes accepted batches to a local queue file (`ndjson` stream).

3. **Stream processing (Python)**
   - Reads ingestion queue incrementally via an offset checkpoint.
   - Validates each event, runs multimodal fusion + autonomy inference, enriches valid events, and routes:
     - valid -> processed events file
     - invalid -> DLQ file
   - Supports DLQ replay.
   - Includes a benchmark CLI for multimodal latency and throughput measurements.

4. **Storage and indexing (Python)**
   - Indexes processed stream output into SQLite (`events` table).
   - Stores queryable metadata and raw event JSON.
   - Uses incremental checkpointing and duplicate-safe inserts.

5. **Query and ML access (Python / FastAPI + CLI)**
   - Query API:
     - `GET /events`
     - `GET /events/{event_id}`
     - `POST /datasets/export`
   - ML export CLI writes:
     - dataset JSONL
     - dataset manifest JSON

6. **Observability (Python)**
   - Computes backlog, drop ratio, index lag, and pipeline counters.
   - Emits alert conditions when thresholds are crossed.
   - Can write observability report JSON.

## Language Split (Python + C++)

- **C++:** edge runtime simulator + event packaging/transport simulation (`edge/simulator/cpp`).
- **Python:** ingestion, streaming, storage indexing, querying, observability, and dataset export.

This mirrors a common autonomy split: performance-sensitive edge logic in C++, cloud/data pipeline in Python.

## Repository Layout

```text
docs/
  architecture/
  telemetry_spec/
edge/
  simulator/
    python/
    cpp/
ingestion/
  api/
  tests/
stream/
  processor/
  tests/
storage/
  indexer/
  tests/
query/
  api/
  tests/
ml/
  exporter/
observability/
  tests/
```

## Quick Start (End-To-End)

### 1) Generate edge telemetry

Python edge path:

```bash
python edge/simulator/python/main.py --steps 120 --seed 7
```

C++ edge path:

```bash
cmake -S edge/simulator/cpp -B edge/simulator/cpp/build
cmake --build edge/simulator/cpp/build
./edge/simulator/cpp/build/Debug/drivecore_sim --steps 120 --seed 7
```

### 2) Run ingestion API

```bash
python -m pip install -r ingestion/requirements.txt
uvicorn ingestion.api.main:app --reload --port 8080
```

### 3) Process stream queue

```bash
python -m stream.processor.main run-once
python -m stream.processor.main replay-dlq
```

### 4) Index processed events

```bash
python -m storage.indexer.main
```

### 5) Query and export datasets

```bash
uvicorn query.api.main:app --reload --port 8090
python -m ml.exporter.main --event-type hard_brake --limit 1000
```

### 6) Run observability checks

```bash
python -m observability.main
python -m observability.main --write-report observability/reports/latest.json
```

### 7) Benchmark multimodal inference performance

```bash
python -m stream.processor.benchmark --events 10000 --warmup 500 --seed 7
```

Output includes throughput (`events/sec`) and latency percentiles (`p50`, `p95`, `p99`) in microseconds.
