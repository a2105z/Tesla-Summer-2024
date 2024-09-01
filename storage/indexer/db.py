from __future__ import annotations

import sqlite3
from pathlib import Path


# Ensure schema.
def ensure_schema(db_path: Path) -> None:
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type_ts ON events(event_type, event_ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_vehicle_ts ON events(vehicle_id, event_ts)")
        conn.commit()

