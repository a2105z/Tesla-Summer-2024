from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from .autonomy import build_autonomy_annotation


@dataclass
class BenchmarkResult:
    total_events: int
    warmup_events: int
    total_duration_s: float
    throughput_events_per_s: float
    latency_us_min: float
    latency_us_p50: float
    latency_us_p95: float
    latency_us_p99: float
    latency_us_max: float


    # Convert data into dict format.
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Parse command-line options for this workflow.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DriveCore multimodal autonomy benchmark")
    parser.add_argument("--events", type=int, default=10000, help="Number of measured events")
    parser.add_argument("--warmup", type=int, default=500, help="Warmup events before timing")
    parser.add_argument("--seed", type=int, default=7, help="Deterministic random seed")
    return parser.parse_args()


# Build a deterministic synthetic event for repeatable benchmarks.
def make_synthetic_event(index: int, rng: random.Random) -> Dict[str, Any]:
    event_type = rng.choice(["hard_brake", "lane_departure", "sudden_obstacle"])
    return {
        "event_id": f"bench_evt_{index:08d}",
        "event_type": event_type,
        "timestamp": 1710000000.0 + index * 0.05,
        "vehicle_id": "bench_vehicle_001",
        "operator_command": rng.choice(["slow down", "maintain speed", "pull over", "reroute"]),
        "vision": {
            "frame_id": f"frame_{index:08d}",
            "lighting": rng.choice(["day", "night"]),
            "scene_hint": rng.choice(["clear_path", "near_obstacle", "dense_traffic"]),
        },
        "state": {
            "speed_mps": round(rng.uniform(0.0, 35.0), 3),
            "brake_force": round(rng.uniform(0.0, 1.0), 3),
            "lane_offset_m": round(rng.uniform(-1.0, 1.0), 3),
            "obstacle_distance_m": round(rng.uniform(1.0, 60.0), 3),
            "steering_deg": round(rng.uniform(-25.0, 25.0), 3),
            "camera_frame_id": f"frame_{index:08d}",
        },
    }


# Compute percentile values from microsecond latency samples.
def percentile_us(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    if percentile <= 0:
        return min(values)
    if percentile >= 100:
        return max(values)
    sorted_values = sorted(values)
    rank = (percentile / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


# Run latency and throughput benchmarks for multimodal autonomy inference.
def run_benchmark(total_events: int, warmup_events: int, seed: int) -> BenchmarkResult:
    rng = random.Random(seed)
    for idx in range(warmup_events):
        build_autonomy_annotation(make_synthetic_event(idx, rng))

    latencies_us: List[float] = []
    bench_start = time.perf_counter()
    for idx in range(total_events):
        event = make_synthetic_event(warmup_events + idx, rng)
        event_start = time.perf_counter_ns()
        build_autonomy_annotation(event)
        event_end = time.perf_counter_ns()
        latencies_us.append((event_end - event_start) / 1000.0)
    bench_end = time.perf_counter()

    duration = max(1e-9, bench_end - bench_start)
    throughput = total_events / duration
    return BenchmarkResult(
        total_events=total_events,
        warmup_events=warmup_events,
        total_duration_s=round(duration, 6),
        throughput_events_per_s=round(throughput, 2),
        latency_us_min=round(min(latencies_us), 3),
        latency_us_p50=round(percentile_us(latencies_us, 50), 3),
        latency_us_p95=round(percentile_us(latencies_us, 95), 3),
        latency_us_p99=round(percentile_us(latencies_us, 99), 3),
        latency_us_max=round(max(latencies_us), 3),
    )


# Run the main entrypoint for this module.
def main() -> None:
    args = parse_args()
    result = run_benchmark(total_events=args.events, warmup_events=args.warmup, seed=args.seed)
    print(json.dumps({"benchmark": result.to_dict()}, separators=(",", ":")))


if __name__ == "__main__":
    main()

