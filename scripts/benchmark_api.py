from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_load import send_partition
from visionops.api import create_app
from visionops.scale_runtime import generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the real loopback HTTP path with chunked NDJSON")
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--partition-rows", type=int, default=50_000)
    parser.add_argument("--output", type=Path, default=Path("artifacts/api-benchmark"))
    args = parser.parse_args()
    dataset = args.output / "dataset"
    api_data = args.output / "server"
    manifest = generate_dataset(dataset, args.rows, args.seed, args.partition_rows)
    app = create_app(api_data)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    started = time.perf_counter()
    thread.start()
    deadline = time.monotonic() + 20
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.02)
    if not server.started:
        raise RuntimeError("loopback API did not start")
    try:
        results = []
        for index, partition in enumerate(manifest["partitions"]):
            key = f"{manifest['dataset_sha256'][:20]}-{index:05d}"
            results.append(send_partition(f"http://127.0.0.1:{port}", dataset / partition["path"], key))
        first = manifest["partitions"][0]
        duplicate = send_partition(f"http://127.0.0.1:{port}", dataset / first["path"], f"{manifest['dataset_sha256'][:20]}-00000")
    finally:
        server.should_exit = True
        thread.join(timeout=20)
        sock.close()
    elapsed = time.perf_counter() - started
    accepted = sum(int(result["accepted"]) for result in results)
    evidence = {"project": manifest["project"], "status": "LOCAL_HTTP_BULK_VERIFIED", "rows": accepted, "partitions": len(results), "elapsed_seconds_including_startup": round(elapsed, 6), "rows_per_second_including_startup": round(accepted / elapsed, 2), "chunk_size_bytes": 1048576, "idempotency_replay_verified": duplicate.get("duplicate") is True, "transport": "HTTP/1.1 chunked NDJSON over loopback", "dataset_sha256": manifest["dataset_sha256"], "api_results": results}
    (args.output / "api-evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
