from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from observability.config import ObservabilitySettings  # noqa: E402
from observability.monitor import ObservabilityMonitor  # noqa: E402


# Handle internal logic for write lines.
def _write_lines(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for idx in range(count):
            handle.write(f'{{"n":{idx}}}\n')


# Handle internal logic for seed db.
def _seed_db(path: Path, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY)")
        for idx in range(rows):
            conn.execute("INSERT OR REPLACE INTO events (event_id) VALUES (?)", (f"evt_{idx}",))
        conn.commit()


# Verify that observability collects metrics and alerts behaves as expected.
def test_observability_collects_metrics_and_alerts(tmp_path: Path) -> None:
    queue = tmp_path / "queue.ndjson"
    offset = tmp_path / "offset.txt"
    processed = tmp_path / "processed.ndjson"
    dlq = tmp_path / "dlq.ndjson"
    db = tmp_path / "events.db"
    _write_lines(queue, 20)
    offset.write_text("5", encoding="utf-8")
    _write_lines(processed, 10)
    _write_lines(dlq, 2)
    _seed_db(db, 8)

    settings = ObservabilitySettings(
        queue_path=queue,
        stream_offset_path=offset,
        processed_events_path=processed,
        dlq_path=dlq,
        db_path=db,
        drop_alert_threshold=0.05,
        backlog_alert_threshold=10,
    )
    report = ObservabilityMonitor(settings).collect()
    assert report.queue_batches == 20
    assert report.queue_backlog_batches == 15
    assert report.processed_events == 10
    assert report.dlq_events == 2
    assert report.indexed_events == 8
    assert any(alert.startswith("drop_ratio_high") for alert in report.alerts)
    assert any(alert.startswith("queue_backlog_high") for alert in report.alerts)
    assert "indexer_lagging:processed_gt_indexed" in report.alerts

