from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from visionops.api import create_app
from visionops.scale_config import BULK_ENDPOINT
from visionops.scale_runtime import generate_dataset, process_dataset


def test_generated_dataset_is_reproducible_and_streamed(tmp_path: Path) -> None:
    left = generate_dataset(tmp_path / "left", rows=250, seed=42, partition_rows=100)
    right = generate_dataset(tmp_path / "right", rows=250, seed=42, partition_rows=100)
    assert left["dataset_sha256"] == right["dataset_sha256"]
    assert len(left["partitions"]) == 3
    report = process_dataset(tmp_path / "left", tmp_path / "report")
    assert report["rows"] == 250
    assert report["status"] == "LOCAL_SCALE_VERIFIED"
    assert (tmp_path / "report" / "dashboard.html").exists()


def test_bulk_api_health_idempotency_and_validation(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "api"))
    assert client.get("/health/live").json() == {"status": "live"}
    assert client.get("/health/ready").status_code == 200
    generated = generate_dataset(tmp_path / "input", rows=4, seed=7, partition_rows=4)
    body = (tmp_path / "input" / generated["partitions"][0]["path"]).read_bytes()
    headers = {"Idempotency-Key": "test-batch-0001", "Content-Type": "application/x-ndjson", "X-Request-ID": "request-123"}
    first = client.post(BULK_ENDPOINT, content=body, headers=headers)
    assert first.status_code == 202
    assert first.json()["accepted"] == 4
    assert first.headers["X-Request-ID"] == "request-123"
    duplicate = client.post(BULK_ENDPOINT, content=body, headers=headers)
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert client.post(BULK_ENDPOINT, content=b"{}\n", headers={"Idempotency-Key": "invalid-record-01", "Content-Type": "application/x-ndjson"}).status_code == 422
    assert client.post(BULK_ENDPOINT, content=body, headers={"Idempotency-Key": "wrong-media-0001", "Content-Type": "application/json"}).status_code == 415
    assert client.post(BULK_ENDPOINT, content=body).status_code == 400
    metrics = client.get("/metrics").text
    assert "portfolio_bulk_accepted_records" in metrics
