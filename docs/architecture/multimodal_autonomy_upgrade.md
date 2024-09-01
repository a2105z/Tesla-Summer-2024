# DriveCore Multimodal Autonomy Upgrade

## Goal

Add a lightweight multimodal autonomy layer on top of the telemetry pipeline so events are not only routed, but also interpreted for decision and anomaly context.

## Inputs

- Telemetry state (`speed`, `brake`, `lane offset`, `obstacle distance`, `steering`)
- Vision metadata (`camera_frame_id`, lighting/scene hints)
- Optional text command (`operator_command`)

## Processing

The stream enrichment stage now executes:

1. Vision embedding generation (deterministic hash from frame IDs)
2. Command signal extraction (mapped intent bias)
3. Multimodal fusion risk score
4. Decision inference (`proceed`, `maintain_lane_and_monitor`, `controlled_slowdown`, `emergency_brake`)
5. Anomaly detection with reason tags

## Output

Each processed event includes:

- `enrichment.autonomy.fusion`
- `enrichment.autonomy.decision`
- `enrichment.autonomy.anomaly`

This keeps DriveCore practical (no heavy GPU stack) while still demonstrating multimodal autonomy reasoning in the pipeline.
