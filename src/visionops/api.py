from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from .scale_config import BULK_ENDPOINT, PROJECT
from .scale_runtime import validate_record


KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


class LocalBulkStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.objects = root / "objects"
        self.database = root / "idempotency.sqlite3"
        self.objects.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS requests (key TEXT PRIMARY KEY, status TEXT NOT NULL, response TEXT, updated_at REAL NOT NULL)")

    def begin(self, key: str) -> dict[str, object] | None:
        with sqlite3.connect(self.database, timeout=20) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT status, response FROM requests WHERE key = ?", (key,)).fetchone()
            if row and row[0] == "completed":
                connection.commit()
                return json.loads(row[1])
            if row and row[0] == "started":
                connection.commit()
                raise HTTPException(status_code=409, detail="idempotency key is already in progress")
            connection.execute("INSERT OR REPLACE INTO requests(key,status,response,updated_at) VALUES(?, 'started', NULL, ?)", (key, time.time()))
            connection.commit()
        return None

    def complete(self, key: str, payload: dict[str, object]) -> None:
        with sqlite3.connect(self.database) as connection:
            connection.execute("UPDATE requests SET status='completed', response=?, updated_at=? WHERE key=?", (json.dumps(payload), time.time(), key))

    def fail(self, key: str) -> None:
        with sqlite3.connect(self.database) as connection:
            connection.execute("UPDATE requests SET status='failed', updated_at=? WHERE key=?", (time.time(), key))


def create_app(data_root: Path | None = None) -> FastAPI:
    root = data_root or Path(os.environ.get("BULK_DATA_ROOT", "artifacts/api"))
    store = LocalBulkStore(root)
    counters = {"requests": 0, "accepted_records": 0, "duplicates": 0, "rejected": 0}
    lock = threading.Lock()
    max_records = int(os.environ.get("BULK_MAX_RECORDS", "1000000"))
    max_bytes = int(os.environ.get("BULK_MAX_BYTES", str(1024 * 1024 * 1024)))
    max_line_bytes = int(os.environ.get("BULK_MAX_LINE_BYTES", str(1024 * 1024)))
    app = FastAPI(title=f"{PROJECT} bulk API", version="1.0.0")

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:128]
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.3f}"
        return response

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def ready() -> dict[str, str]:
        with sqlite3.connect(store.database) as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "ready"}

    @app.get("/v1/status")
    def status() -> dict[str, object]:
        return {"project": PROJECT, "bulk_endpoint": BULK_ENDPOINT, "storage": "local-ndjson-sqlite", "limits": {"records": max_records, "bytes": max_bytes, "line_bytes": max_line_bytes}, "counters": dict(counters)}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> str:
        return "\n".join(f'portfolio_bulk_{name}{{project="{PROJECT}"}} {value}' for name, value in counters.items()) + "\n"

    @app.post(BULK_ENDPOINT)
    async def ingest(request: Request) -> Response:
        key = request.headers.get("Idempotency-Key", "")
        if not KEY_PATTERN.fullmatch(key):
            raise HTTPException(status_code=400, detail="Idempotency-Key must be 8-128 safe characters")
        content_type = request.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/x-ndjson":
            raise HTTPException(status_code=415, detail="Content-Type must be application/x-ndjson")
        duplicate = store.begin(key)
        if duplicate is not None:
            with lock:
                counters["duplicates"] += 1
            return JSONResponse({**duplicate, "duplicate": True}, status_code=200)
        object_id = hashlib.sha256(key.encode()).hexdigest()[:24]
        target = store.objects / f"{object_id}.ndjson"
        partial = target.with_suffix(".partial")
        row_count = 0
        byte_count = 0
        digest = hashlib.sha256()
        buffer = b""
        try:
            with partial.open("wb") as handle:
                async for chunk in request.stream():
                    byte_count += len(chunk)
                    if byte_count > max_bytes:
                        raise HTTPException(status_code=413, detail="request exceeds byte limit")
                    buffer += chunk
                    if len(buffer) > max_line_bytes and b"\n" not in buffer:
                        raise HTTPException(status_code=413, detail="NDJSON line exceeds byte limit")
                    while b"\n" in buffer:
                        raw, buffer = buffer.split(b"\n", 1)
                        if not raw.strip():
                            continue
                        if len(raw) > max_line_bytes:
                            raise HTTPException(status_code=413, detail="NDJSON line exceeds byte limit")
                        try:
                            record = json.loads(raw)
                        except (json.JSONDecodeError, UnicodeDecodeError) as error:
                            raise HTTPException(status_code=422, detail=f"invalid NDJSON at record {row_count + 1}: {error}") from error
                        errors = validate_record(record)
                        if errors:
                            raise HTTPException(status_code=422, detail={"record": row_count + 1, "errors": errors})
                        normalized = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
                        handle.write(normalized)
                        digest.update(normalized)
                        row_count += 1
                        if row_count > max_records:
                            raise HTTPException(status_code=413, detail="request exceeds record limit")
                if buffer.strip():
                    if len(buffer) > max_line_bytes:
                        raise HTTPException(status_code=413, detail="NDJSON line exceeds byte limit")
                    try:
                        record = json.loads(buffer)
                    except (json.JSONDecodeError, UnicodeDecodeError) as error:
                        raise HTTPException(status_code=422, detail=f"invalid final NDJSON record: {error}") from error
                    errors = validate_record(record)
                    if errors:
                        raise HTTPException(status_code=422, detail={"record": row_count + 1, "errors": errors})
                    normalized = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
                    handle.write(normalized)
                    digest.update(normalized)
                    row_count += 1
                    if row_count > max_records:
                        raise HTTPException(status_code=413, detail="request exceeds record limit")
            if row_count == 0:
                raise HTTPException(status_code=422, detail="empty NDJSON body")
            os.replace(partial, target)
            payload = {"project": PROJECT, "accepted": row_count, "bytes_received": byte_count, "object": target.name, "sha256": digest.hexdigest(), "duplicate": False}
            store.complete(key, payload)
            with lock:
                counters["requests"] += 1
                counters["accepted_records"] += row_count
            return JSONResponse(payload, status_code=202)
        except Exception:
            partial.unlink(missing_ok=True)
            store.fail(key)
            with lock:
                counters["rejected"] += 1
            raise

    return app


app = create_app()
