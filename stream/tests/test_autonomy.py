from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stream.processor.autonomy import build_autonomy_annotation  # noqa: E402


# Build a representative telemetry event for autonomy tests.
def _event(speed: float, brake: float, obstacle_distance: float, command: str | None) -> dict:
    return {
        "event_id": "evt_demo",
        "event_type": "hard_brake",
        "timestamp": 1710001111.1,
        "vehicle_id": "veh-demo",
        "operator_command": command,
        "state": {
            "speed_mps": speed,
            "brake_force": brake,
            "lane_offset_m": 0.2,
            "obstacle_distance_m": obstacle_distance,
            "steering_deg": 1.2,
            "camera_frame_id": "frame_000321",
        },
    }


# Verify that multimodal fusion returns decision and anomaly structures.
def test_autonomy_annotation_structure() -> None:
    annotation = build_autonomy_annotation(_event(speed=26.0, brake=0.95, obstacle_distance=3.5, command="slow down"))
    assert "fusion" in annotation
    assert "decision" in annotation
    assert "anomaly" in annotation
    assert annotation["decision"]["action"] in {
        "proceed",
        "maintain_lane_and_monitor",
        "controlled_slowdown",
        "emergency_brake",
    }


# Verify that high-risk telemetry patterns produce anomaly signals.
def test_autonomy_annotation_flags_high_risk() -> None:
    annotation = build_autonomy_annotation(_event(speed=30.0, brake=0.98, obstacle_distance=2.0, command="pull over"))
    assert annotation["anomaly"]["is_anomaly"] is True
    assert len(annotation["anomaly"]["reasons"]) >= 1

