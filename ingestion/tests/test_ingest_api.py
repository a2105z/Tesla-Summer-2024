from __future__ import annotations

import base64
import gzip
import importlib
import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


# Handle internal logic for compressed payload.
def _compressed_payload(events: list[dict]) -> str:
    ndjson = "\n".join(json.dumps(event, separators=(",", ":")) for event in events).encode("utf-8")
    return base64.b64encode(gzip.compress(ndjson)).decode("ascii")


# Handle internal logic for event.
def _event(event_id: str = "evt_001") -> dict:
    return {
        "schema_version": "1.0",
        "event_id": event_id,
        "event_type": "hard_brake",
        "timestamp": 1710000001.1,
        "vehicle_id": "vehicle_sim_001",
        "source": {"device_type": "edge_simulator", "firmware_version": "wk3-4", "simulator": "python"},
        "state": {
            "timestamp": 1710000001.1,
            "speed_mps": 24.3,
            "brake_force": 0.93,
            "lane_offset_m": 0.02,
            "obstacle_distance_m": 22.0,
            "steering_deg": 1.0,
            "camera_frame_id": "frame_001",
        },
    }


# Handle internal logic for batch.
def _batch(batch_id: str = "batch_000001") -> dict:
    events = [_event("evt_001"), _event("evt_002")]
    return {
        "batch_id": batch_id,
        "schema_version": "1.0",
        "vehicle_id": "vehicle_sim_001",
        "event_count": 2,
        "encoding": "ndjson",
        "compression": "gzip",
        "payload_b64": _compressed_payload(events),
    }


# Handle internal logic for set test env.
def _set_test_env(tmp_path: Path) -> None:
    os.environ["DRIVECORE_API_KEYS"] = "test-token"
    os.environ["DRIVECORE_QUEUE_PATH"] = str(tmp_path / "queue.ndjson")
    os.environ["DRIVECORE_IDEMPOTENCY_DB"] = str(tmp_path / "idempotency.db")
    os.environ["DRIVECORE_PUBLISH_FAIL_RATE"] = "0.0"


# Handle internal logic for create client.
def _create_client() -> TestClient:
    module_name = "ingestion.api.main"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
        app = sys.modules[module_name].app
    else:
        app = importlib.import_module(module_name).app
    return TestClient(app)


# Verify that ingest success behaves as expected.
def test_ingest_success(tmp_path: Path) -> None:
    _set_test_env(tmp_path)
    client = _create_client()
    response = client.post(
        "/ingest",
        headers={"Authorization": "Bearer test-token"},
        json={"batches": [_batch()]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted_batches"] == 1
    assert body["duplicate_batches"] == 0
    assert body["decoded_events"] == 2


# Verify that ingest requires auth behaves as expected.
def test_ingest_requires_auth(tmp_path: Path) -> None:
    _set_test_env(tmp_path)
    client = _create_client()
    response = client.post("/ingest", json={"batches": [_batch()]})
    assert response.status_code == 401


# Verify that ingest idempotency behaves as expected.
def test_ingest_idempotency(tmp_path: Path) -> None:
    _set_test_env(tmp_path)
    client = _create_client()
    headers = {"Authorization": "Bearer test-token", "X-Idempotency-Key": "req-123"}
    first = client.post("/ingest", headers=headers, json={"batches": [_batch("batch_000101")]})
    second = client.post("/ingest", headers=headers, json={"batches": [_batch("batch_000101")]})
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate_batches"] == 1
    assert second.json()["accepted_batches"] == 0

