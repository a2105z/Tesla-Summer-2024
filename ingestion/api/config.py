from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Handle internal logic for workspace root.


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    api_keys: set[str]
    queue_path: Path
    idempotency_db_path: Path
    publish_fail_rate: float

    # From env.
    @classmethod
    def from_env(cls) -> "Settings":
        default_root = _workspace_root() / "ingestion" / "data"
        queue_path = Path(os.getenv("DRIVECORE_QUEUE_PATH", str(default_root / "queue.ndjson")))
        idempotency_db_path = Path(
            os.getenv("DRIVECORE_IDEMPOTENCY_DB", str(default_root / "idempotency.db"))
        )
        api_keys_env = os.getenv("DRIVECORE_API_KEYS", "dev-token")
        api_keys = {token.strip() for token in api_keys_env.split(",") if token.strip()}
        fail_rate = float(os.getenv("DRIVECORE_PUBLISH_FAIL_RATE", "0.0"))
        return cls(
            api_keys=api_keys,
            queue_path=queue_path,
            idempotency_db_path=idempotency_db_path,
            publish_fail_rate=max(0.0, min(1.0, fail_rate)),
        )

