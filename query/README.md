# DriveCore Query API (Week 9-10)

Provides retrieval endpoints for ML engineers and telemetry analysis.

## Run

```bash
uvicorn query.api.main:app --reload --port 8090
```

## Endpoints

- `GET /health`
- `GET /events`
  - Optional filters:
    - `event_type`
    - `min_speed`
    - `max_speed`
    - `vehicle_id`
    - `start_ts`
    - `end_ts`
    - `limit`
- `GET /events/{event_id}`
- `POST /datasets/export`
  - Optional filters:
    - `event_type`
    - `min_speed`
    - `max_speed`
    - `limit`
