# DriveCore Week 3-4 Edge Transport Design

## Goal

Move from simple event emission to realistic edge telemetry transport behavior:
- retain temporal context around events
- reduce network overhead with batching and compression
- tolerate transient cloud transport failures with retries

## Edge Pipeline

1. Simulator emits `VehicleState` ticks.
2. Detector identifies autonomy-significant triggers.
3. Ring buffer captures pre-trigger context.
4. Pending captures collect post-trigger context ticks.
5. Completed event windows are packaged into event envelopes.
6. Events are grouped into transmission batches.
7. Batches are compressed (`gzip`) and encoded for wire transfer.
8. Retry queue handles transient send failures with backoff and jitter.

Note: Python agent uses `gzip`; C++ local dev agent keeps payload uncompressed (`compression=none`) to avoid external compression dependencies in Week 3-4.

## Context Window Semantics

- `pre_context_ticks`: number of states retained before trigger
- `post_context_ticks`: number of states retained after trigger
- each emitted event includes:
  - trigger state
  - pre-context state array
  - post-context state array

This approximates edge-side clip extraction logic used for autonomy replay/training.

## Batch Flush Policy

Batch is transmitted when either condition is met:
- event count >= `batch_size`
- elapsed time >= `flush_interval_s`

This prevents both network spam and excessive event latency.

## Retry Policy

- Immediate first send attempt
- On failure:
  - exponential backoff: `base_delay * 2^(attempt-1)`
  - random jitter added to reduce synchronized retries
- drop after `max_retries` attempts

## Metrics

Tracked by the Python telemetry agent:
- `states_processed`
- `events_detected`
- `events_packaged`
- `batches_sent`
- `batches_dropped`
- `transport_failures`
- `retry_attempts`
- `max_retry_queue_depth`
