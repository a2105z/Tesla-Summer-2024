# DriveCore Week 9-10 Storage + Query Design

## Goal

Store processed telemetry in a queryable format and provide retrieval APIs for ML/data workflows.

## Implemented Components

1. **Indexer (`storage/indexer`)**
   - Reads `processed_events.ndjson`
   - Persists metadata + raw JSON to SQLite
   - Uses checkpoint offset for incremental indexing
2. **Storage schema**
   - `events` table with:
     - event metadata (type, vehicle, timestamp)
     - kinematic fields (speed, brake, lane offset, obstacle distance, steering)
     - enrichment fields (weather, batch_id)
     - full raw event JSON
3. **Query API (`query/api`)**
   - `GET /events` with filters
   - `GET /events/{event_id}` for direct lookup

## Why this is practical

- Keeps setup simple (SQLite, no extra services)
- Supports retrieval patterns needed for ML curation
- Easy migration path to PostgreSQL in later phase
