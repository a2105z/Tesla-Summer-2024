# DriveCore Week 1-2 Architecture

## Objective

Define a telemetry foundation that mirrors autonomy telemetry requirements:
- detect high-value edge cases on the vehicle computer
- reduce unnecessary data transfer
- keep events structured for downstream cloud processing

## End-to-End Flow (Current Scope)

1. Vehicle simulator generates state at fixed time intervals.
2. Detector evaluates state transitions for event triggers.
3. Triggered events are serialized into schema-compliant payloads.
4. Events are emitted as newline-delimited JSON for future ingestion wiring.

## Edge State Model

Each simulator tick emits:
- `timestamp`
- `speed_mps`
- `brake_force` (0.0 - 1.0)
- `lane_offset_m`
- `obstacle_distance_m`
- `steering_deg`
- `camera_frame_id`

## Event Types (v1)

### hard_brake
Triggered when:
- `brake_force > 0.8`
- `speed_mps > 18.0`

### lane_departure
Triggered when:
- `abs(lane_offset_m) > 0.5`

### sudden_obstacle
Triggered when:
- `obstacle_distance_m < 8.0`
- `speed_mps > 10.0`

## Design Notes

- Deterministic mode via random seed for reproducible testing
- Rare event injection to emulate edge-case mining
- Identical event semantics implemented in both Python and C++

## Week 3-4 Handoff

- Add payload batching and compression
- Add local ring buffer for pre/post event context
- Add transport client and retry policy
