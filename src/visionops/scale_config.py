from __future__ import annotations

import hashlib
import math
import random
from datetime import UTC, date, datetime, timedelta


PROJECT = 'visionops-multicloud'
BULK_ENDPOINT = '/v1/detections/bulk'
REQUIRED_FIELDS = ('record_id', 'camera_id', 'captured_at', 'zone_id', 'object_class', 'confidence')
CATEGORY_FIELD = 'object_class'
NUMERIC_FIELDS = ('confidence', 'count')


def stable_id(project: str, seed: int, index: int) -> str:
    return hashlib.sha256(f"{project}:{seed}:{index}".encode()).hexdigest()[:24]


def stable_rng(seed: int, index: int) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))

def generate_record(index: int, seed: int) -> dict[str, object]:
    rng = stable_rng(seed, index)
    captured = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index * 2)
    classes = ("person", "vehicle", "forklift")
    return {"record_id": stable_id(PROJECT, seed, index), "camera_id": f"cam-{index % 250:03d}", "captured_at": captured.isoformat(), "zone_id": f"zone-{index % 40:02d}", "object_class": classes[index % len(classes)], "confidence": round(0.55 + rng.random() * 0.45, 4), "count": 1 + rng.randint(0, 8)}

