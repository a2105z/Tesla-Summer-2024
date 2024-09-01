# DriveCore Ingestion Service (Week 5-6)

Cloud entry point for edge telemetry batch envelopes.

## Features

- Bearer-token authentication
- Batch envelope validation (`ndjson` + `gzip`/`none`)
- Event payload decode and schema-shape checks
- Idempotency dedupe with SQLite store
- Queue publish to local NDJSON stream file
- Retry-aware behavior via `503` on publish failure

## Run

```bash
cd ingestion
python -m pip install -r requirements.txt
uvicorn api.main:app --reload --port 8080
```

## Environment Variables

- `DRIVECORE_API_KEYS`: comma-separated API tokens (default: `dev-token`)
- `DRIVECORE_QUEUE_PATH`: output queue file path
- `DRIVECORE_IDEMPOTENCY_DB`: SQLite idempotency DB path
- `DRIVECORE_PUBLISH_FAIL_RATE`: simulated queue failure probability (`0.0` to `1.0`)

## API

- `GET /health`
- `POST /ingest`
  - Headers:
    - `Authorization: Bearer <token>`
    - Optional: `X-Idempotency-Key: <request-key>`
  - Body:
    - `{ "batches": [<batch-envelope>, ...] }`
