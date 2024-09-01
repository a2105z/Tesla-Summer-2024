from __future__ import annotations

import base64
import gzip
import json
import random
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any, Deque, Dict, List, Optional

from detector import detect_event
from models import VehicleState


@dataclass
class AgentConfig:
    pre_context_ticks: int = 20
    post_context_ticks: int = 30
    batch_size: int = 10
    flush_interval_s: float = 1.0
    max_retries: int = 4
    retry_base_delay_s: float = 0.2
    retry_jitter_s: float = 0.15
    transport_fail_rate: float = 0.2
    compression: str = "gzip"


@dataclass
class PendingCapture:
    event_id: str
    event_type: str
    trigger_state: Dict[str, Any]
    pre_context: List[Dict[str, Any]]
    post_context: List[Dict[str, Any]]
    remaining_post_ticks: int


@dataclass
class RetryItem:
    batch: Dict[str, Any]
    available_at: float
    attempts: int = 0


@dataclass
class AgentMetrics:
    states_processed: int = 0
    events_detected: int = 0
    events_packaged: int = 0
    batches_sent: int = 0
    batches_dropped: int = 0
    transport_failures: int = 0
    retry_attempts: int = 0
    max_retry_queue_depth: int = 0


    # Convert data into dict format.
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VehicleSimulator:


    # Initialize this object with the inputs it needs.
    def __init__(self, seed: int, vehicle_id: str, base_timestamp: float = 1710000000.0) -> None:
        self._rng = random.Random(seed)
        self.vehicle_id = vehicle_id
        self._speed = 12.0
        self._lane_offset = 0.0
        self._obstacle_distance = 50.0
        self._base_timestamp = base_timestamp


    # Handle internal logic for next state.
    def _next_state(self, tick: int) -> VehicleState:
        accel = self._rng.uniform(-2.0, 2.5)
        self._speed = max(0.0, self._speed + accel * 0.1)
        self._lane_offset += self._rng.uniform(-0.04, 0.04)
        self._lane_offset = max(-1.2, min(1.2, self._lane_offset))
        self._obstacle_distance = max(1.0, self._obstacle_distance + self._rng.uniform(-3.0, 3.0))
        brake_force = max(0.0, min(1.0, self._rng.uniform(0.0, 0.35)))

        if tick % 35 == 0:
            brake_force = self._rng.uniform(0.85, 1.0)
            self._speed = max(18.5, self._speed + self._rng.uniform(4.0, 9.0))
        if tick % 40 == 0:
            self._lane_offset = self._rng.choice([-0.7, 0.72, -0.9, 0.95])
        if tick % 45 == 0:
            self._obstacle_distance = self._rng.uniform(3.0, 7.5)
            self._speed = max(10.5, self._speed)

        steering_deg = self._lane_offset * 18.0 + self._rng.uniform(-2.0, 2.0)
        timestamp = self._base_timestamp + tick * 0.1
        return VehicleState(
            timestamp=timestamp,
            speed_mps=round(self._speed, 3),
            brake_force=round(brake_force, 3),
            lane_offset_m=round(self._lane_offset, 3),
            obstacle_distance_m=round(self._obstacle_distance, 3),
            steering_deg=round(steering_deg, 3),
            camera_frame_id=f"frame_{tick:06d}",
        )


    # Run states for this stage.
    def run_states(self, steps: int) -> List[VehicleState]:
        return [self._next_state(tick) for tick in range(1, steps + 1)]


class MockIngestionTransport:


    # Initialize this object with the inputs it needs.
    def __init__(self, rng: random.Random, fail_rate: float, emit_payloads: bool) -> None:
        self._rng = rng
        self._fail_rate = fail_rate
        self._emit_payloads = emit_payloads


    # Send a batch through the mock transport layer.
    def send(self, batch: Dict[str, Any]) -> bool:
        if self._rng.random() < self._fail_rate:
            return False
        if self._emit_payloads:
            print(json.dumps(batch, separators=(",", ":")))
        return True


class EdgeTelemetryAgent:


    # Initialize this object with the inputs it needs.
    def __init__(self, vehicle_id: str, seed: int, config: AgentConfig, emit_payloads: bool = True) -> None:
        self.vehicle_id = vehicle_id
        self.config = config
        self.metrics = AgentMetrics()
        self._rng = random.Random(seed + 991)
        self._ring_buffer: Deque[Dict[str, Any]] = deque(maxlen=config.pre_context_ticks + 1)
        self._pending: List[PendingCapture] = []
        self._batch_events: List[Dict[str, Any]] = []
        self._batch_start_ts: Optional[float] = None
        self._retry_queue: Deque[RetryItem] = deque()
        self._transport = MockIngestionTransport(
            rng=self._rng,
            fail_rate=config.transport_fail_rate,
            emit_payloads=emit_payloads,
        )


    # Process states.
    def process_states(self, states: List[VehicleState]) -> AgentMetrics:
        for state in states:
            self._on_state(state)
        self._finalize_pending_captures()
        self._flush_batch(force=True, now_ts=states[-1].timestamp if states else 0.0)
        self._drain_retry_queue_until_empty(end_ts=(states[-1].timestamp if states else 0.0) + 10.0)
        return self.metrics


    # Handle internal logic for on state.
    def _on_state(self, state: VehicleState) -> None:
        state_dict = state.to_dict()
        self.metrics.states_processed += 1
        self._ring_buffer.append(state_dict)
        event_type = detect_event(state)
        if event_type is not None:
            self.metrics.events_detected += 1
            self._pending.append(
                PendingCapture(
                    event_id=str(uuid.uuid4()),
                    event_type=event_type,
                    trigger_state=state_dict,
                    pre_context=list(self._ring_buffer)[:-1],
                    post_context=[],
                    remaining_post_ticks=self.config.post_context_ticks,
                )
            )

        completed_indexes: List[int] = []
        for idx, pending in enumerate(self._pending):
            if state_dict["timestamp"] == pending.trigger_state["timestamp"]:
                continue
            if pending.remaining_post_ticks > 0:
                pending.post_context.append(state_dict)
                pending.remaining_post_ticks -= 1
            if pending.remaining_post_ticks == 0:
                completed_indexes.append(idx)

        for idx in reversed(completed_indexes):
            pending = self._pending.pop(idx)
            self._batch_events.append(self._package_event(pending))
            self.metrics.events_packaged += 1
            if self._batch_start_ts is None:
                self._batch_start_ts = state.timestamp

        should_flush_for_size = len(self._batch_events) >= self.config.batch_size
        should_flush_for_time = (
            self._batch_start_ts is not None and (state.timestamp - self._batch_start_ts) >= self.config.flush_interval_s
        )
        if should_flush_for_size or should_flush_for_time:
            self._flush_batch(force=False, now_ts=state.timestamp)

        self._drain_retry_queue_due(now_ts=state.timestamp)


    # Handle internal logic for finalize pending captures.
    def _finalize_pending_captures(self) -> None:
        while self._pending:
            pending = self._pending.pop(0)
            self._batch_events.append(self._package_event(pending))
            self.metrics.events_packaged += 1


    # Handle internal logic for package event.
    def _package_event(self, pending: PendingCapture) -> Dict[str, Any]:
        operator_command = self._infer_operator_command(pending)
        vision_payload = self._build_vision_payload(pending)
        return {
            "schema_version": "1.0",
            "event_id": pending.event_id,
            "event_type": pending.event_type,
            "timestamp": pending.trigger_state["timestamp"],
            "vehicle_id": self.vehicle_id,
            "source": {
                "device_type": "edge_simulator",
                "firmware_version": "wk3-4",
                "simulator": "python",
            },
            "operator_command": operator_command,
            "vision": vision_payload,
            "state": pending.trigger_state,
            "context": {
                "pre_context": pending.pre_context,
                "post_context": pending.post_context,
                "pre_ticks": self.config.pre_context_ticks,
                "post_ticks": self.config.post_context_ticks,
            },
        }

    # Handle internal logic for infer operator command.
    def _infer_operator_command(self, pending: PendingCapture) -> str:
        event_type = pending.event_type
        if event_type == "hard_brake":
            return "slow down"
        if event_type == "lane_departure":
            return "maintain speed"
        if event_type == "sudden_obstacle":
            return "pull over"
        return "reroute"

    # Handle internal logic for build vision payload.
    def _build_vision_payload(self, pending: PendingCapture) -> Dict[str, Any]:
        frame_id = str(pending.trigger_state.get("camera_frame_id", "frame_000000"))
        lighting = "day" if int(pending.trigger_state.get("timestamp", 0)) % 2 == 0 else "night"
        obstacle_hint = (
            "near_obstacle"
            if float(pending.trigger_state.get("obstacle_distance_m", 999.0)) < 10.0
            else "clear_path"
        )
        return {"frame_id": frame_id, "lighting": lighting, "scene_hint": obstacle_hint}


    # Handle internal logic for flush batch.
    def _flush_batch(self, force: bool, now_ts: float) -> None:
        if not self._batch_events:
            return
        if not force and len(self._batch_events) < self.config.batch_size and self._batch_start_ts is not None:
            if (now_ts - self._batch_start_ts) < self.config.flush_interval_s:
                return
        batch_events = self._batch_events
        self._batch_events = []
        self._batch_start_ts = None
        batch_payload = self._build_batch_payload(batch_events)
        self._retry_queue.append(RetryItem(batch=batch_payload, available_at=now_ts))
        self.metrics.max_retry_queue_depth = max(self.metrics.max_retry_queue_depth, len(self._retry_queue))
        self._drain_retry_queue_due(now_ts=now_ts)


    # Handle internal logic for build batch payload.
    def _build_batch_payload(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        ndjson = "\n".join(json.dumps(event, separators=(",", ":")) for event in events).encode("utf-8")
        compressed = gzip.compress(ndjson)
        return {
            "batch_id": str(uuid.uuid4()),
            "schema_version": "1.0",
            "vehicle_id": self.vehicle_id,
            "event_count": len(events),
            "encoding": "ndjson",
            "compression": self.config.compression,
            "payload_b64": base64.b64encode(compressed).decode("ascii"),
        }


    # Handle internal logic for drain retry queue due.
    def _drain_retry_queue_due(self, now_ts: float) -> None:
        if not self._retry_queue:
            return
        pending_backlog: Deque[RetryItem] = deque()
        while self._retry_queue:
            item = self._retry_queue.popleft()
            if item.available_at > now_ts:
                pending_backlog.append(item)
                continue
            if self._attempt_send(item, now_ts):
                continue
            pending_backlog.append(item)
        self._retry_queue = pending_backlog


    # Handle internal logic for drain retry queue until empty.
    def _drain_retry_queue_until_empty(self, end_ts: float) -> None:
        virtual_now = end_ts
        guard = 0
        while self._retry_queue and guard < 10000:
            guard += 1
            next_ready = min(item.available_at for item in self._retry_queue)
            virtual_now = max(virtual_now, next_ready)
            self._drain_retry_queue_due(now_ts=virtual_now)
            virtual_now += 0.01


    # Handle internal logic for attempt send.
    def _attempt_send(self, item: RetryItem, now_ts: float) -> bool:
        item.attempts += 1
        success = self._transport.send(item.batch)
        if success:
            self.metrics.batches_sent += 1
            return True
        self.metrics.transport_failures += 1
        if item.attempts > self.config.max_retries:
            self.metrics.batches_dropped += 1
            return True
        self.metrics.retry_attempts += 1
        backoff = self.config.retry_base_delay_s * (2 ** (item.attempts - 1))
        jitter = self._rng.uniform(0.0, self.config.retry_jitter_s)
        item.available_at = now_ts + backoff + jitter
        self.metrics.max_retry_queue_depth = max(self.metrics.max_retry_queue_depth, len(self._retry_queue) + 1)
        return False


# Run edge pipeline for this stage.
def run_edge_pipeline(
    steps: int,
    seed: int,
    vehicle_id: str,
    config: Optional[AgentConfig] = None,
    emit_payloads: bool = True,
) -> AgentMetrics:
    runtime_config = config or AgentConfig()
    simulator = VehicleSimulator(seed=seed, vehicle_id=vehicle_id)
    agent = EdgeTelemetryAgent(vehicle_id=vehicle_id, seed=seed, config=runtime_config, emit_payloads=emit_payloads)
    states = simulator.run_states(steps)
    return agent.process_states(states)

