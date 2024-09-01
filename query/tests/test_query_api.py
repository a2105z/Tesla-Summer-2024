from __future__ import annotations

import importlib
import os
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient


# Handle internal logic for seed db.
def _seed_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                vehicle_id TEXT NOT NULL,
                event_ts REAL NOT NULL,
                speed_mps REAL NOT NULL,
                brake_force REAL NOT NULL,
                lane_offset_m REAL NOT NULL,
                obstacle_distance_m REAL NOT NULL,
                steering_deg REAL NOT NULL,
                weather TEXT,
                batch_id TEXT,
                raw_event_json TEXT NOT NULL,
                indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO events (
                event_id, event_type, vehicle_id, event_ts,
                speed_mps, brake_force, lane_offset_m, obstacle_distance_m, steering_deg,
                weather, batch_id, raw_event_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evt1",
                "hard_brake",
                "veh-1",
                1710000000.1,
                28.5,
                0.91,
                0.02,
                15.0,
                1.0,
                "clear",
                "b1",
                '{"event_id":"evt1","event_type":"hard_brake","vehicle_id":"veh-1","timestamp":1710000000.1,"state":{"speed_mps":28.5}}',
            ),
        )
        conn.commit()


# Handle internal logic for client with db.
def _client_with_db(db_path: Path) -> TestClient:
    os.environ["DRIVECORE_STORAGE_DB_PATH"] = str(db_path)
    os.environ["DRIVECORE_EXPORT_DIR"] = str(db_path.parent / "exports")
    module_name = "query.api.main"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
        app = sys.modules[module_name].app
    else:
        app = importlib.import_module(module_name).app
    return TestClient(app)


# Verify that query filters and lookup behaves as expected.
def test_query_filters_and_lookup(tmp_path: Path) -> None:
    db_path = tmp_path / "events.db"
    _seed_db(db_path)
    client = _client_with_db(db_path)

    response = client.get("/events", params={"event_type": "hard_brake", "min_speed": 25})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["event_id"] == "evt1"

    single = client.get("/events/evt1")
    assert single.status_code == 200
    assert single.json()["event_id"] == "evt1"

    export = client.post("/datasets/export", params={"event_type": "hard_brake", "limit": 10})
    assert export.status_code == 200
    export_body = export.json()["export"]
    assert export_body["event_count"] == 1
    assert Path(export_body["output_path"]).exists()
    assert Path(export_body["manifest_path"]).exists()

