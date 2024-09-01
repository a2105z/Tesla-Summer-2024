from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from ml.exporter.config import ExportSettings
from ml.exporter.service import DatasetExporter
from .config import QuerySettings
from .repository import EventRepository


settings = QuerySettings.from_env()
repository = EventRepository(settings.db_path)
export_settings = ExportSettings.from_env()
exporter = DatasetExporter(export_settings.db_path, export_settings.export_dir)

app = FastAPI(
    title="DriveCore Query API",
    version="0.1.0",
    description="Week 9-10 query surface for telemetry and ML data retrieval.",
)


# Return a quick health response for this service.
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Return filtered telemetry events for querying.
@app.get("/events")
async def events(
    event_type: str | None = Query(default=None),
    min_speed: float | None = Query(default=None),
    max_speed: float | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    start_ts: float | None = Query(default=None),
    end_ts: float | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict:
    rows = repository.list_events(
        event_type=event_type,
        min_speed=min_speed,
        max_speed=max_speed,
        vehicle_id=vehicle_id,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
    )
    return {"count": len(rows), "events": rows}


# Return one event by its unique identifier.
@app.get("/events/{event_id}")
async def event_by_id(event_id: str) -> dict:
    row = repository.get_event(event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return row


# Export a filtered dataset for ML training workflows.
@app.post("/datasets/export")
async def export_dataset(
    event_type: str | None = Query(default=None),
    min_speed: float | None = Query(default=None),
    max_speed: float | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=50000),
) -> dict:
    result = exporter.export_jsonl(
        event_type=event_type,
        min_speed=min_speed,
        max_speed=max_speed,
        limit=limit,
    )
    return {"status": "ok", "export": result.to_dict()}

