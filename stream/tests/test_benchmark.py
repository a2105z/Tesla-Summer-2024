from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stream.processor.benchmark import percentile_us, run_benchmark  # noqa: E402


# Verify that percentile interpolation stays within expected bounds.
def test_percentile_us_interpolates_values() -> None:
    values = [10.0, 20.0, 30.0, 40.0]
    assert percentile_us(values, 0) == 10.0
    assert percentile_us(values, 100) == 40.0
    assert 20.0 <= percentile_us(values, 50) <= 30.0


# Verify that benchmark runner returns complete throughput and latency metrics.
def test_run_benchmark_returns_metrics() -> None:
    result = run_benchmark(total_events=200, warmup_events=20, seed=7)
    assert result.total_events == 200
    assert result.warmup_events == 20
    assert result.total_duration_s > 0
    assert result.throughput_events_per_s > 0
    assert result.latency_us_min >= 0
    assert result.latency_us_p50 >= result.latency_us_min
    assert result.latency_us_p95 >= result.latency_us_p50
    assert result.latency_us_p99 >= result.latency_us_p95
    assert result.latency_us_max >= result.latency_us_p99

