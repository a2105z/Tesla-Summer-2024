# DriveCore Week 5-6 Ingestion Design

## Goal

Receive telemetry from edge devices reliably and prepare it for stream processing.

## Implemented Components

1. **Ingestion API (FastAPI)**
   - `POST /ingest` for batch submissions
   - `GET /health` for uptime checks
2. **Auth**
   - Bearer token validation via `Authorization` header
3. **Validation**
   - Batch envelope structure checks
   - `payload_b64` decode
   - `gzip` decompression (when specified)
   - NDJSON event parsing and required-field validation
4. **Idempotency**
   - Request/batch dedupe with SQLite-backed key store
5. **Queue publishing**
   - File-backed queue stream (`queue.ndjson`)
   - Simulated transient failure mode for retry testing

## Retry Contract

When queue publish fails, service returns:
- HTTP `503`
- `Retry-After: 1`
- Response message instructing retry with same idempotency key

This enforces at-least-once request behavior while preventing duplicate inserts.

## Handoff to Week 7-8

- Replace file queue with Kafka/Redis streams producer
- Add consumer service for validation/enrichment/routing
- Add DLQ and replay commands
