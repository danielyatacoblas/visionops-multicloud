from __future__ import annotations

import argparse
import http.client
import json
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from visionops.scale_config import BULK_ENDPOINT
from visionops.scale_runtime import PROFILES, generate_dataset


def send_partition(base_url: str, path: Path, key: str) -> dict[str, object]:
    parsed = urlparse(base_url)
    connection_class = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    connection = connection_class(parsed.hostname, parsed.port, timeout=120)
    def chunks():
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                yield chunk
    endpoint = (parsed.path.rstrip("/") + BULK_ENDPOINT) or BULK_ENDPOINT
    connection.request("POST", endpoint, body=chunks(), headers={"Content-Type": "application/x-ndjson", "Idempotency-Key": key, "X-Request-ID": str(uuid.uuid4())}, encode_chunked=True)
    response = connection.getresponse()
    payload = json.loads(response.read())
    connection.close()
    if response.status not in {200, 202}:
        raise RuntimeError(f"API returned {response.status}: {payload}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic partitioned NDJSON without holding the dataset in memory")
    parser.add_argument("--profile", choices=PROFILES, default="smoke")
    parser.add_argument("--rows", type=int, help="Override profile row count")
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--partition-rows", type=int, default=50_000)
    parser.add_argument("--output", type=Path, default=Path("artifacts/scale-input"))
    parser.add_argument("--api-url", help="Optional API base URL, for example http://127.0.0.1:8000")
    args = parser.parse_args()
    manifest = generate_dataset(args.output, args.rows or PROFILES[args.profile], args.seed, args.partition_rows)
    if args.api_url:
        manifest["api_results"] = [send_partition(args.api_url, args.output / part["path"], f"{manifest['dataset_sha256'][:20]}-{index:05d}") for index, part in enumerate(manifest["partitions"])]
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
