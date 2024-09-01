# DriveCore Week 7-8 Stream Processing Design

## Goal

Process incoming telemetry in near-real-time with a simple, testable pipeline.

## Implemented Pipeline

1. Read new queue batches from `ingestion/data/queue.ndjson`
2. Validate event integrity and numeric ranges
3. Enrich valid events with:
   - inferred weather
   - batch metadata
   - processing timestamp
4. Route valid events to processed storage
5. Route invalid events to DLQ with reason codes
6. Persist line offset checkpoint for incremental processing

## Why this is intentionally simple

- Uses NDJSON files instead of Kafka to reduce setup complexity
- Preserves stream concepts: consumer offsets, validation, enrichment, routing, DLQ, replay
- Easy to replace source/sink with Kafka/Redis in next phase

## Commands

- Process new queue data:
  - `python -m stream.processor.main run-once`
- Replay DLQ:
  - `python -m stream.processor.main replay-dlq`
