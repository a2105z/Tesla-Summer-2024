from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Handle internal logic for workspace root.


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class StreamSettings:
    queue_path: Path
    processed_events_path: Path
    dlq_path: Path
    offset_path: Path

    # From env.
    @classmethod
    def from_env(cls) -> "StreamSettings":
        root = _workspace_root()
        data_dir = root / "stream" / "data"
        queue_default = root / "ingestion" / "data" / "queue.ndjson"
        return cls(
            queue_path=Path(os.getenv("DRIVECORE_QUEUE_PATH", str(queue_default))),
            processed_events_path=Path(
                os.getenv("DRIVECORE_PROCESSED_EVENTS_PATH", str(data_dir / "processed_events.ndjson"))
            ),
            dlq_path=Path(os.getenv("DRIVECORE_DLQ_PATH", str(data_dir / "dlq.ndjson"))),
            offset_path=Path(os.getenv("DRIVECORE_STREAM_OFFSET_PATH", str(data_dir / "offset.txt"))),
        )

