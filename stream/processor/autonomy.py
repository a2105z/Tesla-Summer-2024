from __future__ import annotations

import hashlib
from typing import Any, Dict, List


# Build a compact deterministic vision signal from frame identifiers.
def vision_embedding(camera_frame_id: str) -> List[float]:
    digest = hashlib.sha256(camera_frame_id.encode("utf-8")).digest()
    return [round(byte / 255.0, 4) for byte in digest[:6]]


# Convert optional natural-language commands into steering intent hints.
def command_signal(command: str | None) -> Dict[str, float]:
    normalized = (command or "").strip().lower()
    command_map = {
        "slow down": {"speed_bias": -0.25, "risk_boost": 0.12},
        "reroute": {"speed_bias": -0.10, "risk_boost": 0.04},
        "pull over": {"speed_bias": -0.40, "risk_boost": 0.20},
        "maintain speed": {"speed_bias": 0.05, "risk_boost": -0.02},
    }
    return command_map.get(normalized, {"speed_bias": 0.0, "risk_boost": 0.0})


# Fuse telemetry, synthetic vision, and command data into one feature set.
def fuse_modalities(event: Dict[str, Any]) -> Dict[str, Any]:
    state = event.get("state", {})
    command = event.get("operator_command")
    camera_frame_id = str(state.get("camera_frame_id", "frame_000000"))
    embed = vision_embedding(camera_frame_id)
    cmd = command_signal(command)

    speed = float(state.get("speed_mps", 0.0))
    brake = float(state.get("brake_force", 0.0))
    lane_offset = abs(float(state.get("lane_offset_m", 0.0)))
    obstacle_distance = float(state.get("obstacle_distance_m", 100.0))

    fused_risk = (
        min(1.0, speed / 45.0) * 0.30
        + brake * 0.25
        + min(1.0, lane_offset / 1.0) * 0.20
        + (1.0 - min(1.0, obstacle_distance / 40.0)) * 0.20
        + sum(embed[:3]) / 3.0 * 0.05
        + cmd["risk_boost"]
    )
    return {
        "camera_frame_id": camera_frame_id,
        "vision_embedding": embed,
        "command": command,
        "command_signal": cmd,
        "fused_risk_score": round(max(0.0, min(1.0, fused_risk)), 4),
    }


# Infer a high-level autonomy decision from fused multimodal features.
def infer_decision(fused: Dict[str, Any]) -> Dict[str, Any]:
    risk = float(fused.get("fused_risk_score", 0.0))
    if risk >= 0.75:
        action = "emergency_brake"
    elif risk >= 0.55:
        action = "controlled_slowdown"
    elif risk >= 0.35:
        action = "maintain_lane_and_monitor"
    else:
        action = "proceed"
    return {"action": action, "confidence": round(min(0.99, 0.45 + risk * 0.5), 4)}


# Flag potential anomalies that should be prioritized for review or training.
def detect_anomaly(event: Dict[str, Any], fused: Dict[str, Any]) -> Dict[str, Any]:
    state = event.get("state", {})
    speed = float(state.get("speed_mps", 0.0))
    lane_offset = abs(float(state.get("lane_offset_m", 0.0)))
    obstacle_distance = float(state.get("obstacle_distance_m", 999.0))
    brake = float(state.get("brake_force", 0.0))
    risk = float(fused.get("fused_risk_score", 0.0))

    rules = []
    if brake > 0.9 and speed > 20.0:
        rules.append("high_speed_hard_brake")
    if lane_offset > 0.8:
        rules.append("extreme_lane_offset")
    if obstacle_distance < 4.0 and speed > 12.0:
        rules.append("close_obstacle_at_speed")
    if risk > 0.8:
        rules.append("model_high_risk")

    return {"is_anomaly": len(rules) > 0, "reasons": rules}


# Build the final autonomy block attached to enriched stream events.
def build_autonomy_annotation(event: Dict[str, Any]) -> Dict[str, Any]:
    fused = fuse_modalities(event)
    decision = infer_decision(fused)
    anomaly = detect_anomaly(event, fused)
    return {"fusion": fused, "decision": decision, "anomaly": anomaly}

