from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stream.processor.config import StreamSettings  # noqa: E402
from stream.processor.engine import StreamProcessor  # noqa: E402


# Handle internal logic for write ndjson.
def _write_ndjson(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


# Handle internal logic for event.
def _event(event_id: str, event_type: str = "hard_brake", speed: float = 20.0, brake: float = 0.9) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "timestamp": 1710000000.1,
        "vehicle_id": "veh-1",
        "operator_command": "slow down",
        "vision": {"frame_id": "frame_123", "lighting": "day", "scene_hint": "clear_path"},
        "source": {"device_type": "sim", "firmware_version": "wk3-4"},
        "state": {
            "speed_mps": speed,
            "brake_force": brake,
            "lane_offset_m": 0.0,
            "obstacle_distance_m": 30.0,
            "steering_deg": 0.1,
            "camera_frame_id": "frame_123",
        },
    }


# Verify that run once processes valid and routes invalid behaves as expected.
def test_run_once_processes_valid_and_routes_invalid(tmp_path: Path) -> None:
    queue = tmp_path / "queue.ndjson"
    processed = tmp_path / "processed.ndjson"
    dlq = tmp_path / "dlq.ndjson"
    offset = tmp_path / "offset.txt"
    rows = [
        {
            "batch_id": "b1",
            "event_count": 2,
            "events": [
                _event("evt_ok"),
                _event("evt_bad", brake=2.5),
            ],
        }
    ]
    _write_ndjson(queue, rows)
    settings = StreamSettings(
        queue_path=queue,
        processed_events_path=processed,
        dlq_path=dlq,
        offset_path=offset,
    )
    processor = StreamProcessor(settings)
    metrics = processor.run_once()
    assert metrics.batches_read == 1
    assert metrics.events_seen == 2
    assert metrics.events_processed == 1
    assert metrics.events_dlq == 1
    processed_rows = [json.loads(line) for line in processed.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert processed_rows[0]["enrichment"]["autonomy"]["decision"]["action"] in {
        "proceed",
        "maintain_lane_and_monitor",
        "controlled_slowdown",
        "emergency_brake",
    }


# Verify that replay dlq moves fixed events behaves as expected.
def test_replay_dlq_moves_fixed_events(tmp_path: Path) -> None:
    queue = tmp_path / "queue.ndjson"
    processed = tmp_path / "processed.ndjson"
    dlq = tmp_path / "dlq.ndjson"
    offset = tmp_path / "offset.txt"
    _write_ndjson(
        dlq,
        [
            {"batch_id": "b2", "reason": "speed_negative", "event": _event("evt_fixable", speed=10.0)},
            {"batch_id": "b2", "reason": "still_bad", "event": {"event_id": "broken"}},
        ],
    )
    settings = StreamSettings(
        queue_path=queue,
        processed_events_path=processed,
        dlq_path=dlq,
        offset_path=offset,
    )
    processor = StreamProcessor(settings)
    metrics = processor.replay_dlq()
    assert metrics.replay_processed == 1
    assert metrics.replay_remaining == 1

