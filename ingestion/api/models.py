from __future__ import annotations

import base64
import gzip
import json
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ALLOWED_EVENT_TYPES = {"hard_brake", "lane_departure", "sudden_obstacle"}


class BatchEnvelope(BaseModel):
    batch_id: str = Field(min_length=8)
    schema_version: Literal["1.0"]
    vehicle_id: str = Field(min_length=1)
    event_count: int = Field(ge=1)
    encoding: Literal["ndjson"]
    compression: Literal["gzip", "none"]
    payload_b64: str = Field(min_length=1)

    # Validate base64 before continuing.
    @field_validator("payload_b64")
    @classmethod
    def validate_base64(cls, value: str) -> str:
        try:
            base64.b64decode(value, validate=True)
        except Exception as exc:  # pragma: no cover - strict decode branch
            raise ValueError("payload_b64 is not valid base64") from exc
        return value


    # Decoded ndjson.


    def decoded_ndjson(self) -> bytes:
        raw = base64.b64decode(self.payload_b64)
        if self.compression == "gzip":
            try:
                return gzip.decompress(raw)
            except Exception as exc:
                raise ValueError("gzip payload could not be decompressed") from exc
        return raw


    # Decoded events.


    def decoded_events(self) -> List[Dict[str, Any]]:
        payload = self.decoded_ndjson().decode("utf-8")
        lines = [line for line in payload.splitlines() if line.strip()]
        events: List[Dict[str, Any]] = []
        for line in lines:
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("payload contains invalid JSON lines") from exc
            if not isinstance(parsed, dict):
                raise ValueError("each NDJSON line must be an object")
            _validate_event_shape(parsed)
            events.append(parsed)
        if len(events) != self.event_count:
            raise ValueError("event_count does not match decoded NDJSON event lines")
        return events


class IngestRequest(BaseModel):
    batches: List[BatchEnvelope] = Field(min_length=1, max_length=200)

    # Unique batch ids.
    @model_validator(mode="after")
    def unique_batch_ids(self) -> "IngestRequest":
        ids = [batch.batch_id for batch in self.batches]
        if len(ids) != len(set(ids)):
            raise ValueError("batch_id values must be unique inside one request")
        return self


class IngestResponse(BaseModel):
    status: Literal["ok", "partial"]
    request_id: str
    accepted_batches: int
    duplicate_batches: int
    decoded_events: int


# Handle internal logic for validate event shape.


def _validate_event_shape(event: Dict[str, Any]) -> None:
    required = {"schema_version", "event_id", "event_type", "timestamp", "vehicle_id", "source", "state"}
    missing = required - set(event.keys())
    if missing:
        raise ValueError(f"event missing required keys: {sorted(missing)}")
    if event["event_type"] not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event['event_type']}")
    if not isinstance(event["source"], dict) or not isinstance(event["state"], dict):
        raise ValueError("event source/state must be objects")

