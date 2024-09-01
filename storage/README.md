# DriveCore Storage (Week 9-10)

Indexes processed stream events into a queryable SQLite store.

## Run indexer

```bash
python -m storage.indexer.main
```

## Inputs/Outputs

- Input: `stream/data/processed_events.ndjson`
- Output DB: `storage/data/events.db`
- Offset checkpoint: `storage/data/indexer_offset.txt`

The indexer is incremental and safe to run repeatedly.
