from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict


class PublisherUnavailableError(RuntimeError):
    pass


class FileQueuePublisher:


    # Initialize this object with the inputs it needs.
    def __init__(self, queue_path: Path, fail_rate: float = 0.0, seed: int = 9) -> None:
        self._queue_path = queue_path
        self._queue_path.parent.mkdir(parents=True, exist_ok=True)
        self._fail_rate = fail_rate
        self._rng = random.Random(seed)


    # Publish.
    def publish(self, payload: Dict[str, Any]) -> None:
        if self._rng.random() < self._fail_rate:
            raise PublisherUnavailableError("Transient queue publish failure")
        with self._queue_path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(payload, separators=(",", ":")) + "\n")

