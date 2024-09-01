from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from storage.indexer.config import StorageSettings  # noqa: E402
from storage.indexer.indexer import EventIndexer  # noqa: E402


# Handle internal logic for write lines.
def _write_lines(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


# Handle internal logic for event.
def _event(event_id: str, speed: float = 21.0) -> dict:
    return {
        "event_id": event_id,
        "event_type": "hard_brake",
        "timestamp": 1710000000.1,
        "vehicle_id": "veh-1",
        "state": {
            "speed_mps": speed,
            "brake_force": 0.92,
            "lane_offset_m": 0.0,
            "obstacle_distance_m": 20.0,
            "steering_deg": 0.3,
        },
        "enrichment": {"weather": "clear", "batch_id": "b1"},
    }


# Verify that indexer writes events and skips duplicates behaves as expected.
def test_indexer_writes_events_and_skips_duplicates(tmp_path: Path) -> None:
    processed_path = tmp_path / "processed.ndjson"
    db_path = tmp_path / "events.db"
    offset_path = tmp_path / "offset.txt"
    _write_lines(processed_path, [_event("evt1"), _event("evt2"), _event("evt2")])
    settings = StorageSettings(
        processed_events_path=processed_path,
        sqlite_db_path=db_path,
        offset_path=offset_path,
    )
    indexer = EventIndexer(settings)
    metrics = indexer.run_once()
    assert metrics.lines_seen == 3
    assert metrics.indexed_events == 2
    assert metrics.duplicates_skipped == 1

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert count == 2

