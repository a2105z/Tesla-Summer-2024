from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


class EventRepository:


    # Initialize this object with the inputs it needs.
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)


    # Return a filtered list of events.
    def list_events(
        self,
        event_type: str | None,
        min_speed: float | None,
        max_speed: float | None,
        vehicle_id: str | None,
        start_ts: float | None,
        end_ts: float | None,
        limit: int,
    ) -> List[Dict[str, Any]]:
        where: List[str] = []
        params: List[Any] = []
        if event_type:
            where.append("event_type = ?")
            params.append(event_type)
        if min_speed is not None:
            where.append("speed_mps >= ?")
            params.append(min_speed)
        if max_speed is not None:
            where.append("speed_mps <= ?")
            params.append(max_speed)
        if vehicle_id:
            where.append("vehicle_id = ?")
            params.append(vehicle_id)
        if start_ts is not None:
            where.append("event_ts >= ?")
            params.append(start_ts)
        if end_ts is not None:
            where.append("event_ts <= ?")
            params.append(end_ts)

        query = "SELECT raw_event_json FROM events"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY event_ts DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [json.loads(row[0]) for row in rows]


    # Fetch event from the current source.
    def get_event(self, event_id: str) -> Dict[str, Any] | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT raw_event_json FROM events WHERE event_id = ?", (event_id,)).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

