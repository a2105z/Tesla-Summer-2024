from __future__ import annotations

import argparse
import json

from .config import StreamSettings
from .engine import StreamProcessor


# Parse command-line options for this workflow.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DriveCore Week 7-8 stream processor")
    parser.add_argument(
        "command",
        choices=("run-once", "replay-dlq"),
        help="run-once: process new queue batches, replay-dlq: retry DLQ events",
    )
    return parser.parse_args()


# Run the main entrypoint for this module.
def main() -> None:
    args = parse_args()
    processor = StreamProcessor(StreamSettings.from_env())
    if args.command == "run-once":
        metrics = processor.run_once()
    else:
        metrics = processor.replay_dlq()
    print(json.dumps({"metrics": metrics.to_dict()}, separators=(",", ":")))


if __name__ == "__main__":
    main()

