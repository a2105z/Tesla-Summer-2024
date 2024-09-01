from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Handle internal logic for workspace root.


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class StorageSettings:
    processed_events_path: Path
    sqlite_db_path: Path
    offset_path: Path

    # From env.
    @classmethod
    def from_env(cls) -> "StorageSettings":
        root = _workspace_root()
        storage_data = root / "storage" / "data"
        return cls(
            processed_events_path=Path(
                os.getenv(
                    "DRIVECORE_PROCESSED_EVENTS_PATH",
                    str(root / "stream" / "data" / "processed_events.ndjson"),
                )
            ),
            sqlite_db_path=Path(os.getenv("DRIVECORE_STORAGE_DB_PATH", str(storage_data / "events.db"))),
            offset_path=Path(os.getenv("DRIVECORE_STORAGE_OFFSET_PATH", str(storage_data / "indexer_offset.txt"))),
        )

