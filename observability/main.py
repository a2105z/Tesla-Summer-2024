from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import ObservabilitySettings
from .monitor import ObservabilityMonitor


# Parse command-line options for this workflow.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DriveCore observability monitor")
    parser.add_argument(
        "--write-report",
        type=str,
        default=None,
        help="Optional path to persist report JSON",
    )
    return parser.parse_args()


# Run the main entrypoint for this module.
def main() -> None:
    args = parse_args()
    monitor = ObservabilityMonitor(ObservabilitySettings.from_env())
    if args.write_report:
        report = monitor.write_report(Path(args.write_report))
    else:
        report = monitor.collect()
    print(json.dumps({"observability": report.to_dict()}, separators=(",", ":")))


if __name__ == "__main__":
    main()

