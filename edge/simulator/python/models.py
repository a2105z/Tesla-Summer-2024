from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Any


@dataclass
class VehicleState:
    timestamp: float
    speed_mps: float
    brake_force: float
    lane_offset_m: float
    obstacle_distance_m: float
    steering_deg: float
    camera_frame_id: str


    # Convert data into dict format.
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

