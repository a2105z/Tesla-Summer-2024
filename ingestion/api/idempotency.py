from __future__ import annotations

import sqlite3
from pathlib import Path


class IdempotencyStore:


    # Initialize this object with the inputs it needs.
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()


    # Handle internal logic for initialize.
    def _initialize(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_batches (
                    key TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()


    # Is duplicate.
    def is_duplicate(self, key: str) -> bool:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT 1 FROM processed_batches WHERE key = ?", (key,)).fetchone()
            return row is not None


    # Record.
    def record(self, key: str, batch_id: str) -> bool:
        """
        Returns True when newly recorded, False when already present.
        """
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO processed_batches (key, batch_id) VALUES (?, ?)",
                    (key, batch_id),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

