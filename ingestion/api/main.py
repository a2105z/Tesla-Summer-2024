from __future__ import annotations

import logging
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, status

from .auth import auth_dependency_factory
from .config import Settings
from .idempotency import IdempotencyStore
from .models import IngestRequest, IngestResponse
from .publisher import FileQueuePublisher, PublisherUnavailableError
from .service import IngestService


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("drivecore.ingestion")

settings = Settings.from_env()
idempotency_store = IdempotencyStore(settings.idempotency_db_path)
publisher = FileQueuePublisher(queue_path=settings.queue_path, fail_rate=settings.publish_fail_rate)
service = IngestService(idempotency_store=idempotency_store, publisher=publisher)
auth_dependency = auth_dependency_factory(settings.api_keys)

app = FastAPI(
    title="DriveCore Ingestion Service",
    version="0.1.0",
    description="Week 5-6 cloud ingestion API for batched autonomy telemetry.",
)


# Return a quick health response for this service.
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Accept telemetry batches, validate them, and publish them.
@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    payload: IngestRequest,
    _: str = Depends(auth_dependency),
    x_idempotency_key: str | None = Header(default=None),
) -> IngestResponse:
    request_id = str(uuid.uuid4())
    accepted = 0
    duplicates = 0
    decoded_events = 0

    try:
        for batch in payload.batches:
            result = service.ingest_batch(batch=batch, request_scope_key=x_idempotency_key)
            accepted += result["accepted"]
            duplicates += result["duplicate"]
            decoded_events += result["events"]
    except ValueError as exc:
        logger.warning("request_id=%s validation_error=%s", request_id, exc)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except PublisherUnavailableError as exc:
        logger.warning("request_id=%s queue_unavailable=%s", request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue publish failed. Retry request with same idempotency key.",
            headers={"Retry-After": "1"},
        ) from exc

    logger.info(
        "request_id=%s accepted=%s duplicates=%s decoded_events=%s",
        request_id,
        accepted,
        duplicates,
        decoded_events,
    )

    return IngestResponse(
        status="ok" if duplicates == 0 else "partial",
        request_id=request_id,
        accepted_batches=accepted,
        duplicate_batches=duplicates,
        decoded_events=decoded_events,
    )

