from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Handle internal logic for workspace root.


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


@dataclass
class ObservabilitySettings:
    queue_path: Path
    stream_offset_path: Path
    processed_events_path: Path
    dlq_path: Path
    db_path: Path
    drop_alert_threshold: float
    backlog_alert_threshold: int

    # From env.
    @classmethod
    def from_env(cls) -> "ObservabilitySettings":
        root = _workspace_root()
        return cls(
            queue_path=Path(os.getenv("DRIVECORE_QUEUE_PATH", str(root / "ingestion" / "data" / "queue.ndjson"))),
            stream_offset_path=Path(
                os.getenv("DRIVECORE_STREAM_OFFSET_PATH", str(root / "stream" / "data" / "offset.txt"))
            ),
            processed_events_path=Path(
                os.getenv(
                    "DRIVECORE_PROCESSED_EVENTS_PATH",
                    str(root / "stream" / "data" / "processed_events.ndjson"),
                )
            ),
            dlq_path=Path(os.getenv("DRIVECORE_DLQ_PATH", str(root / "stream" / "data" / "dlq.ndjson"))),
            db_path=Path(os.getenv("DRIVECORE_STORAGE_DB_PATH", str(root / "storage" / "data" / "events.db"))),
            drop_alert_threshold=float(os.getenv("DRIVECORE_DROP_ALERT_THRESHOLD", "0.05")),
            backlog_alert_threshold=int(os.getenv("DRIVECORE_BACKLOG_ALERT_THRESHOLD", "100")),
        )

