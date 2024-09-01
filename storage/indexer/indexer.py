from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import StorageSettings
from .db import ensure_schema


@dataclass
class IndexMetrics:
    lines_seen: int = 0
    indexed_events: int = 0
    duplicates_skipped: int = 0
    parse_errors: int = 0


    # Convert data into dict format.


    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


class EventIndexer:


    # Initialize this object with the inputs it needs.


    def __init__(self, settings: StorageSettings) -> None:
        self.settings = settings
        ensure_schema(self.settings.sqlite_db_path)
        self.settings.offset_path.parent.mkdir(parents=True, exist_ok=True)


    # Run once for this stage.


    def run_once(self) -> IndexMetrics:
        metrics = IndexMetrics()
        lines = self._read_lines(self.settings.processed_events_path)
        start = self._read_offset()
        if start >= len(lines):
            return metrics

        with sqlite3.connect(self.settings.sqlite_db_path) as conn:
            for idx, line in enumerate(lines[start:], start=start + 1):
                metrics.lines_seen += 1
                event = self._parse_line(line)
                if event is None:
                    metrics.parse_errors += 1
                    self._write_offset(idx)
                    continue
                inserted = self._upsert_event(conn, event)
                if inserted:
                    metrics.indexed_events += 1
                else:
                    metrics.duplicates_skipped += 1
                self._write_offset(idx)
            conn.commit()
        return metrics

    # Handle internal logic for read lines.
    @staticmethod
    def _read_lines(path: Path) -> List[str]:
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8").splitlines()

    # Handle internal logic for parse line.
    @staticmethod
    def _parse_line(line: str) -> Dict[str, Any] | None:
        if not line.strip():
            return None
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    # Handle internal logic for upsert event.
    @staticmethod
    def _upsert_event(conn: sqlite3.Connection, event: Dict[str, Any]) -> bool:
        state = event.get("state", {})
        enrichment = event.get("enrichment", {})
        try:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_id, event_type, vehicle_id, event_ts,
                    speed_mps, brake_force, lane_offset_m, obstacle_distance_m, steering_deg,
                    weather, batch_id, raw_event_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event["event_id"]),
                    str(event["event_type"]),
                    str(event["vehicle_id"]),
                    float(event["timestamp"]),
                    float(state["speed_mps"]),
                    float(state["brake_force"]),
                    float(state["lane_offset_m"]),
                    float(state["obstacle_distance_m"]),
                    float(state["steering_deg"]),
                    str(enrichment.get("weather", "")),
                    str(enrichment.get("batch_id", "")),
                    json.dumps(event, separators=(",", ":")),
                ),
            )
        except (KeyError, TypeError, ValueError):
            return False
        return cursor.rowcount == 1


    # Handle internal logic for read offset.


    def _read_offset(self) -> int:
        if not self.settings.offset_path.exists():
            return 0
        raw = self.settings.offset_path.read_text(encoding="utf-8").strip()
        if not raw:
            return 0
        try:
            return max(0, int(raw))
        except ValueError:
            return 0


    # Handle internal logic for write offset.


    def _write_offset(self, line_count: int) -> None:
        self.settings.offset_path.write_text(str(line_count), encoding="utf-8")

