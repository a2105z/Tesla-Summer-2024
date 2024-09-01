from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Handle internal logic for workspace root.


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class ExportSettings:
    db_path: Path
    export_dir: Path

    # From env.
    @classmethod
    def from_env(cls) -> "ExportSettings":
        root = _workspace_root()
        return cls(
            db_path=Path(os.getenv("DRIVECORE_STORAGE_DB_PATH", str(root / "storage" / "data" / "events.db"))),
            export_dir=Path(os.getenv("DRIVECORE_EXPORT_DIR", str(root / "ml" / "exports"))),
        )

