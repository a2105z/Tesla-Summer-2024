from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ExportResult:
    dataset_id: str
    output_path: str
    manifest_path: str
    event_count: int


    # Convert data into dict format.
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DatasetExporter:


    # Initialize this object with the inputs it needs.
    def __init__(self, db_path: Path, export_dir: Path) -> None:
        self._db_path = db_path
        self._export_dir = export_dir
        self._export_dir.mkdir(parents=True, exist_ok=True)


    # Export jsonl.
    def export_jsonl(
        self,
        event_type: str | None,
        min_speed: float | None,
        max_speed: float | None,
        limit: int,
    ) -> ExportResult:
        rows = self._fetch_rows(
            event_type=event_type,
            min_speed=min_speed,
            max_speed=max_speed,
            limit=limit,
        )
        dataset_id = f"dataset_{int(time.time())}"
        output_path = self._export_dir / f"{dataset_id}.jsonl"
        manifest_path = self._export_dir / f"{dataset_id}.manifest.json"

        with output_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(row["raw_event_json"] + "\n")

        manifest = {
            "dataset_id": dataset_id,
            "format": "jsonl",
            "filters": {
                "event_type": event_type,
                "min_speed": min_speed,
                "max_speed": max_speed,
                "limit": limit,
            },
            "event_count": len(rows),
            "source_db_path": str(self._db_path),
            "output_path": str(output_path),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        return ExportResult(
            dataset_id=dataset_id,
            output_path=str(output_path),
            manifest_path=str(manifest_path),
            event_count=len(rows),
        )


    # Handle internal logic for fetch rows.
    def _fetch_rows(
        self,
        event_type: str | None,
        min_speed: float | None,
        max_speed: float | None,
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

        query = "SELECT event_id, raw_event_json FROM events"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY event_ts DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self._db_path) as conn:
            fetched = conn.execute(query, tuple(params)).fetchall()
        return [{"event_id": row[0], "raw_event_json": row[1]} for row in fetched]

