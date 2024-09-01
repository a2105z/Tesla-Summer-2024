from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Handle internal logic for workspace root.


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class QuerySettings:
    db_path: Path

    # From env.
    @classmethod
    def from_env(cls) -> "QuerySettings":
        root = _workspace_root()
        db_path = Path(os.getenv("DRIVECORE_STORAGE_DB_PATH", str(root / "storage" / "data" / "events.db")))
        return cls(db_path=db_path)

