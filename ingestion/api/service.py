from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict

from .idempotency import IdempotencyStore
from .models import BatchEnvelope
from .publisher import FileQueuePublisher, PublisherUnavailableError


@dataclass
class IngestStats:
    accepted_batches: int = 0
    duplicate_batches: int = 0
    decoded_events: int = 0


class IngestService:


    # Initialize this object with the inputs it needs.


    def __init__(self, idempotency_store: IdempotencyStore, publisher: FileQueuePublisher) -> None:
        self._idempotency_store = idempotency_store
        self._publisher = publisher


    # Ingest batch.


    def ingest_batch(self, batch: BatchEnvelope, request_scope_key: str | None) -> Dict[str, int]:
        dedupe_key = self._dedupe_key(batch=batch, request_scope_key=request_scope_key)
        if self._idempotency_store.is_duplicate(dedupe_key):
            return {"accepted": 0, "duplicate": 1, "events": 0}

        events = batch.decoded_events()
        publish_payload = {
            "batch_id": batch.batch_id,
            "vehicle_id": batch.vehicle_id,
            "schema_version": batch.schema_version,
            "event_count": batch.event_count,
            "events": events,
        }
        self._publisher.publish(publish_payload)
        self._idempotency_store.record(dedupe_key, batch.batch_id)
        return {"accepted": 1, "duplicate": 0, "events": len(events)}

    # Handle internal logic for dedupe key.
    @staticmethod
    def _dedupe_key(batch: BatchEnvelope, request_scope_key: str | None) -> str:
        if request_scope_key:
            return f"{request_scope_key}:{batch.batch_id}"
        payload_hash = hashlib.sha256(batch.payload_b64.encode("utf-8")).hexdigest()
        return f"batch:{batch.batch_id}:{payload_hash}"


__all__ = ["IngestService", "IngestStats", "PublisherUnavailableError"]

