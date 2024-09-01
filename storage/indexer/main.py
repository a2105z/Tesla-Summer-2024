from __future__ import annotations

import json

from .config import StorageSettings
from .indexer import EventIndexer


# Run the main entrypoint for this module.
def main() -> None:
    indexer = EventIndexer(StorageSettings.from_env())
    metrics = indexer.run_once()
    print(json.dumps({"metrics": metrics.to_dict()}, separators=(",", ":")))


if __name__ == "__main__":
    main()

