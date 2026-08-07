from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from visionops.scale_runtime import process_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate checksums and aggregate a partitioned dataset in streaming mode")
    parser.add_argument("--input", type=Path, default=Path("artifacts/scale-input"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/scale-report"))
    args = parser.parse_args()
    print(json.dumps(process_dataset(args.input, args.output), indent=2))


if __name__ == "__main__":
    main()
