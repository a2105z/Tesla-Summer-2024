from __future__ import annotations

import argparse
import json
import sys

from simulator import AgentConfig, run_edge_pipeline


# Parse command-line options for this workflow.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DriveCore Python edge telemetry pipeline")
    parser.add_argument("--steps", type=int, default=120, help="Number of ticks to simulate")
    parser.add_argument("--seed", type=int, default=7, help="Deterministic random seed")
    parser.add_argument("--vehicle-id", type=str, default="vehicle_sim_001", help="Vehicle identifier")
    parser.add_argument("--pre-context", type=int, default=20, help="Number of ticks retained before trigger")
    parser.add_argument("--post-context", type=int, default=30, help="Number of ticks captured after trigger")
    parser.add_argument("--batch-size", type=int, default=10, help="Events per transmission batch")
    parser.add_argument("--flush-interval", type=float, default=1.0, help="Flush interval in seconds")
    parser.add_argument("--max-retries", type=int, default=4, help="Max retries before dropping a batch")
    parser.add_argument("--retry-base-delay", type=float, default=0.2, help="Retry base delay in seconds")
    parser.add_argument("--retry-jitter", type=float, default=0.15, help="Retry jitter in seconds")
    parser.add_argument("--transport-fail-rate", type=float, default=0.2, help="Mock transport failure probability")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress emitted batch payloads and print metrics only",
    )
    return parser.parse_args()


# Run the main entrypoint for this module.
def main() -> None:
    args = parse_args()
    config = AgentConfig(
        pre_context_ticks=args.pre_context,
        post_context_ticks=args.post_context,
        batch_size=args.batch_size,
        flush_interval_s=args.flush_interval,
        max_retries=args.max_retries,
        retry_base_delay_s=args.retry_base_delay,
        retry_jitter_s=args.retry_jitter,
        transport_fail_rate=args.transport_fail_rate,
    )
    metrics = run_edge_pipeline(
        steps=args.steps,
        seed=args.seed,
        vehicle_id=args.vehicle_id,
        config=config,
        emit_payloads=not args.quiet,
    )
    print(json.dumps({"metrics": metrics.to_dict()}, separators=(",", ":")), file=sys.stderr)


if __name__ == "__main__":
    main()

