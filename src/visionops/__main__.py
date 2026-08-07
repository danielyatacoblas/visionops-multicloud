from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description='Analítica de ocupación por video con privacidad')
    parser.add_argument("--input", type=Path, default=Path("data/sample"))
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    result = run(args.input, args.output)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
