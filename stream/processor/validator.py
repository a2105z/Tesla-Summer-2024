from __future__ import annotations

from typing import Any, Dict, Tuple


VALID_EVENT_TYPES = {"hard_brake", "lane_departure", "sudden_obstacle"}


# Validate event before continuing.
def validate_event(event: Dict[str, Any]) -> Tuple[bool, str]:
    required = {"event_id", "event_type", "timestamp", "vehicle_id", "source", "state"}
    missing = required - set(event.keys())
    if missing:
        return False, f"missing_keys:{sorted(missing)}"

    if event["event_type"] not in VALID_EVENT_TYPES:
        return False, "invalid_event_type"

    if "operator_command" in event and not isinstance(event["operator_command"], str):
        return False, "operator_command_not_string"

    if "vision" in event and not isinstance(event["vision"], dict):
        return False, "vision_not_object"

    state = event.get("state")
    if not isinstance(state, dict):
        return False, "state_not_object"

    numeric_fields = ("speed_mps", "brake_force", "lane_offset_m", "obstacle_distance_m", "steering_deg")
    for key in numeric_fields:
        value = state.get(key)
        if not isinstance(value, (int, float)):
            return False, f"invalid_state_field:{key}"

    brake_force = float(state["brake_force"])
    if brake_force < 0.0 or brake_force > 1.0:
        return False, "brake_force_out_of_range"

    if float(state["speed_mps"]) < 0.0:
        return False, "speed_negative"

    if float(state["obstacle_distance_m"]) < 0.0:
        return False, "obstacle_distance_negative"

    return True, "ok"

