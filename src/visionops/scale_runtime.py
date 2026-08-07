from __future__ import annotations

import hashlib
import html
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Iterator

from .scale_config import CATEGORY_FIELD, NUMERIC_FIELDS, PROJECT, REQUIRED_FIELDS, generate_record


PROFILES = {"smoke": 1_000, "medium": 100_000, "large": 1_000_000}


def validate_record(record: object) -> list[str]:
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    missing = [name for name in REQUIRED_FIELDS if name not in record]
    errors = [f"missing field: {name}" for name in missing]
    if "record_id" in record and not str(record["record_id"]).strip():
        errors.append("record_id cannot be empty")
    for name in NUMERIC_FIELDS:
        if name in record and not isinstance(record[name], (int, float)):
            errors.append(f"{name} must be numeric")
    return errors


def generate_dataset(output_dir: Path, rows: int, seed: int, partition_rows: int = 50_000) -> dict[str, object]:
    if rows < 1:
        raise ValueError("rows must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    partitions: list[dict[str, object]] = []
    started = time.perf_counter()
    for start in range(0, rows, partition_rows):
        end = min(start + partition_rows, rows)
        name = f"part-{len(partitions):05d}.ndjson"
        target = output_dir / name
        partial = target.with_suffix(".partial")
        digest = hashlib.sha256()
        with partial.open("wb") as handle:
            for index in range(start, end):
                payload = (json.dumps(generate_record(index, seed), ensure_ascii=False, separators=(",", ":")) + "\n").encode()
                digest.update(payload)
                handle.write(payload)
        os.replace(partial, target)
        partitions.append({"path": name, "rows": end - start, "sha256": digest.hexdigest(), "bytes": target.stat().st_size})
    elapsed = max(time.perf_counter() - started, 1e-9)
    dataset_hash = hashlib.sha256("".join(str(part["sha256"]) for part in partitions).encode()).hexdigest()
    manifest = {"schema_version": "1.0", "project": PROJECT, "seed": seed, "rows": rows, "partition_rows": partition_rows, "partitions": partitions, "dataset_sha256": dataset_hash, "generation_seconds": round(elapsed, 6), "rows_per_second": round(rows / elapsed, 2)}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def iter_records(input_dir: Path) -> Iterator[dict[str, object]]:
    manifest = json.loads((input_dir / "manifest.json").read_text(encoding="utf-8"))
    for partition in manifest["partitions"]:
        path = input_dir / partition["path"]
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for line_number, raw in enumerate(handle, 1):
                digest.update(raw)
                record = json.loads(raw)
                errors = validate_record(record)
                if errors:
                    raise ValueError(f"{path.name}:{line_number}: {'; '.join(errors)}")
                yield record
        if digest.hexdigest() != partition["sha256"]:
            raise ValueError(f"checksum mismatch: {path.name}")


def process_dataset(input_dir: Path, output_dir: Path) -> dict[str, object]:
    started = time.perf_counter()
    categories: Counter[str] = Counter()
    sums = {name: 0.0 for name in NUMERIC_FIELDS}
    minimums = {name: float("inf") for name in NUMERIC_FIELDS}
    maximums = {name: float("-inf") for name in NUMERIC_FIELDS}
    rows = 0
    for record in iter_records(input_dir):
        rows += 1
        categories[str(record[CATEGORY_FIELD])] += 1
        for name in NUMERIC_FIELDS:
            value = float(record.get(name, 0))
            sums[name] += value
            minimums[name] = min(minimums[name], value)
            maximums[name] = max(maximums[name], value)
    elapsed = max(time.perf_counter() - started, 1e-9)
    numeric = {name: {"mean": round(sums[name] / rows, 6), "min": minimums[name], "max": maximums[name]} for name in NUMERIC_FIELDS}
    report = {"project": PROJECT, "status": "LOCAL_SCALE_VERIFIED", "rows": rows, "processing_seconds": round(elapsed, 6), "rows_per_second": round(rows / elapsed, 2), "category_field": CATEGORY_FIELD, "top_categories": categories.most_common(20), "numeric_summary": numeric, "memory_strategy": "streaming NDJSON; one record in memory plus bounded aggregates"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "scale-run.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    bars = "".join(f'<div class="bar"><span>{html.escape(name)}</span><i style="width:{max(2, count / max(categories.values()) * 100):.1f}%"></i><b>{count:,}</b></div>' for name, count in categories.most_common(12))
    dashboard = f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{html.escape(PROJECT)} scale evidence</title><style>body{{font-family:Inter,system-ui;background:#07111f;color:#e2e8f0;max-width:1050px;margin:40px auto;padding:0 20px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.card,.panel{{background:#111d2e;border:1px solid #28405f;border-radius:14px;padding:20px}}strong{{display:block;font-size:2rem;color:#38bdf8}}.panel{{margin-top:18px}}.bar{{display:grid;grid-template-columns:160px 1fr 100px;gap:12px;align-items:center;margin:12px 0}}i{{display:block;background:linear-gradient(90deg,#38bdf8,#8b5cf6);height:18px;border-radius:9px}}b{{text-align:right}}small{{color:#94a3b8}}</style><h1>{html.escape(PROJECT)}</h1><p>Evidencia local reproducible · no representa un benchmark de nube.</p><div class="cards"><div class="card"><small>Registros válidos</small><strong>{rows:,}</strong></div><div class="card"><small>Throughput local</small><strong>{rows / elapsed:,.0f}/s</strong></div><div class="card"><small>Tiempo</small><strong>{elapsed:.3f}s</strong></div></div><div class="panel"><h2>Distribución: {html.escape(CATEGORY_FIELD)}</h2>{bars}</div></html>'''
    (output_dir / "dashboard.html").write_text(dashboard, encoding="utf-8")
    return report
