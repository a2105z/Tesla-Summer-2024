from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

from .config import ObservabilitySettings


@dataclass
class ObservabilityReport:
    queue_batches: int
    stream_offset: int
    queue_backlog_batches: int
    processed_events: int
    dlq_events: int
    indexed_events: int
    drop_ratio: float
    alerts: List[str]


    # Convert data into dict format.
    def to_dict(self) -> Dict:
        return asdict(self)


class ObservabilityMonitor:


    # Initialize this object with the inputs it needs.
    def __init__(self, settings: ObservabilitySettings) -> None:
        self.settings = settings


    # Collect cross-pipeline observability metrics.
    def collect(self) -> ObservabilityReport:
        queue_batches = _count_lines(self.settings.queue_path)
        stream_offset = _read_int(self.settings.stream_offset_path)
        backlog = max(0, queue_batches - stream_offset)
        processed = _count_lines(self.settings.processed_events_path)
        dlq = _count_lines(self.settings.dlq_path)
        indexed = _count_db_rows(self.settings.db_path, "events")
        drop_ratio = (dlq / (processed + dlq)) if (processed + dlq) > 0 else 0.0

        alerts: List[str] = []
        if drop_ratio > self.settings.drop_alert_threshold:
            alerts.append(f"drop_ratio_high:{drop_ratio:.3f}")
        if backlog > self.settings.backlog_alert_threshold:
            alerts.append(f"queue_backlog_high:{backlog}")
        if indexed < processed:
            alerts.append("indexer_lagging:processed_gt_indexed")

        return ObservabilityReport(
            queue_batches=queue_batches,
            stream_offset=stream_offset,
            queue_backlog_batches=backlog,
            processed_events=processed,
            dlq_events=dlq,
            indexed_events=indexed,
            drop_ratio=round(drop_ratio, 6),
            alerts=alerts,
        )


    # Write the current observability report to disk.
    def write_report(self, output_path: Path) -> ObservabilityReport:
        report = self.collect()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return report


# Handle internal logic for count lines.
def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


# Handle internal logic for read int.
def _read_int(path: Path) -> int:
    if not path.exists():
        return 0
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


# Handle internal logic for count db rows.
def _count_db_rows(db_path: Path, table: str) -> int:
    if not db_path.exists():
        return 0
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0

