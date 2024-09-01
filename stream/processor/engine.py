from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import StreamSettings
from .enricher import enrich_event
from .validator import validate_event


@dataclass
class StreamMetrics:
    batches_read: int = 0
    events_seen: int = 0
    events_processed: int = 0
    events_dlq: int = 0
    parse_errors: int = 0
    replay_processed: int = 0
    replay_remaining: int = 0


    # Convert data into dict format.


    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


class StreamProcessor:


    # Initialize this object with the inputs it needs.


    def __init__(self, settings: StreamSettings) -> None:
        self.settings = settings
        self._ensure_dirs()


    # Run once for this stage.


    def run_once(self) -> StreamMetrics:
        metrics = StreamMetrics()
        start_line = self._read_offset()
        queue_lines = self._read_lines(self.settings.queue_path)
        if start_line >= len(queue_lines):
            return metrics

        for line_idx, line in enumerate(queue_lines[start_line:], start=start_line + 1):
            batch = self._parse_json(line)
            if batch is None:
                metrics.parse_errors += 1
                self._write_offset(line_idx)
                continue
            metrics.batches_read += 1
            self._process_batch(batch=batch, metrics=metrics)
            self._write_offset(line_idx)
        return metrics


    # Replay dlq.


    def replay_dlq(self) -> StreamMetrics:
        metrics = StreamMetrics()
        entries = self._read_json_lines(self.settings.dlq_path)
        keep_entries: List[Dict[str, Any]] = []
        for entry in entries:
            event = entry.get("event")
            if not isinstance(event, dict):
                keep_entries.append(entry)
                continue
            valid, _ = validate_event(event)
            if valid:
                batch_id = str(entry.get("batch_id", "replay"))
                enriched = enrich_event(event, batch_id=batch_id)
                self._append_json_line(self.settings.processed_events_path, enriched)
                metrics.replay_processed += 1
            else:
                keep_entries.append(entry)
        self._overwrite_json_lines(self.settings.dlq_path, keep_entries)
        metrics.replay_remaining = len(keep_entries)
        return metrics


    # Handle internal logic for process batch.


    def _process_batch(self, batch: Dict[str, Any], metrics: StreamMetrics) -> None:
        batch_id = str(batch.get("batch_id", "unknown"))
        events = batch.get("events", [])
        if not isinstance(events, list):
            metrics.parse_errors += 1
            return
        for event in events:
            metrics.events_seen += 1
            if not isinstance(event, dict):
                metrics.events_dlq += 1
                self._write_dlq(batch_id=batch_id, reason="event_not_object", event={"raw": event})
                continue
            is_valid, reason = validate_event(event)
            if not is_valid:
                metrics.events_dlq += 1
                self._write_dlq(batch_id=batch_id, reason=reason, event=event)
                continue
            enriched = enrich_event(event, batch_id=batch_id)
            self._append_json_line(self.settings.processed_events_path, enriched)
            metrics.events_processed += 1


    # Handle internal logic for write dlq.


    def _write_dlq(self, batch_id: str, reason: str, event: Dict[str, Any]) -> None:
        self._append_json_line(
            self.settings.dlq_path,
            {"batch_id": batch_id, "reason": reason, "event": event},
        )


    # Handle internal logic for ensure dirs.


    def _ensure_dirs(self) -> None:
        for path in (
            self.settings.processed_events_path,
            self.settings.dlq_path,
            self.settings.offset_path,
            self.settings.queue_path,
        ):
            path.parent.mkdir(parents=True, exist_ok=True)

    # Handle internal logic for parse json.
    @staticmethod
    def _parse_json(line: str) -> Dict[str, Any] | None:
        if not line.strip():
            return None
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    # Handle internal logic for read lines.
    @staticmethod
    def _read_lines(path: Path) -> List[str]:
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8").splitlines()

    # Handle internal logic for read json lines.
    @staticmethod
    def _read_json_lines(path: Path) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        if not path.exists():
            return entries
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parsed = StreamProcessor._parse_json(line)
            if parsed is not None:
                entries.append(parsed)
        return entries

    # Handle internal logic for append json line.
    @staticmethod
    def _append_json_line(path: Path, payload: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")

    # Handle internal logic for overwrite json lines.
    @staticmethod
    def _overwrite_json_lines(path: Path, entries: List[Dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry, separators=(",", ":")) + "\n")


    # Handle internal logic for read offset.


    def _read_offset(self) -> int:
        if not self.settings.offset_path.exists():
            return 0
        raw = self.settings.offset_path.read_text(encoding="utf-8").strip()
        if not raw:
            return 0
        try:
            return max(0, int(raw))
        except ValueError:
            return 0


    # Handle internal logic for write offset.


    def _write_offset(self, line_count: int) -> None:
        self.settings.offset_path.write_text(str(line_count), encoding="utf-8")

