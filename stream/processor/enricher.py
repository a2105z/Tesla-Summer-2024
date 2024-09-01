from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .autonomy import build_autonomy_annotation


# Infer weather.
def infer_weather(timestamp: float) -> str:
    # Deterministic pseudo-weather for simulation and repeatable tests.
    slot = int(timestamp // 300) % 4
    return ("clear", "cloudy", "rain", "fog")[slot]


# Enrich event.
def enrich_event(event: Dict[str, Any], batch_id: str) -> Dict[str, Any]:
    enriched = dict(event)
    enriched["enrichment"] = {
        "batch_id": batch_id,
        "weather": infer_weather(float(event["timestamp"])),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "autonomy": build_autonomy_annotation(event),
    }
    return enriched

