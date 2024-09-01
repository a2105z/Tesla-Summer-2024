from __future__ import annotations

import argparse
import json

from .config import ExportSettings
from .service import DatasetExporter


# Parse command-line options for this workflow.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DriveCore dataset export tool")
    parser.add_argument("--event-type", type=str, default=None)
    parser.add_argument("--min-speed", type=float, default=None)
    parser.add_argument("--max-speed", type=float, default=None)
    parser.add_argument("--limit", type=int, default=1000)
    return parser.parse_args()


# Run the main entrypoint for this module.
def main() -> None:
    args = parse_args()
    settings = ExportSettings.from_env()
    exporter = DatasetExporter(settings.db_path, settings.export_dir)
    result = exporter.export_jsonl(
        event_type=args.event_type,
        min_speed=args.min_speed,
        max_speed=args.max_speed,
        limit=args.limit,
    )
    print(json.dumps({"export": result.to_dict()}, separators=(",", ":")))


if __name__ == "__main__":
    main()

