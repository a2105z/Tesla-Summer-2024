from __future__ import annotations

from typing import Optional

from models import VehicleState


# Detect event.
def detect_event(state: VehicleState) -> Optional[str]:
    if state.brake_force > 0.8 and state.speed_mps > 18.0:
        return "hard_brake"
    if abs(state.lane_offset_m) > 0.5:
        return "lane_departure"
    if state.obstacle_distance_m < 8.0 and state.speed_mps > 10.0:
        return "sudden_obstacle"
    return None

