from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path


FORBIDDEN_FIELDS = {"face", "face_embedding", "name", "email", "document_id", "biometric_id"}


def _validate_privacy(frames: list[dict[str, object]]) -> None:
    for frame in frames:
        for detected in frame.get("objects", []):
            forbidden = FORBIDDEN_FIELDS & detected.keys()
            if forbidden:
                raise ValueError(f"biometric or identifying fields are forbidden: {sorted(forbidden)}")


def _heatmap_svg(maximums: dict[str, int], capacities: dict[str, int]) -> str:
    blocks = []
    for index, zone in enumerate(sorted(maximums)):
        count = maximums[zone]
        capacity = capacities[zone]
        ratio = count / capacity if capacity else 1
        color = "#ef4444" if ratio > 1 else "#f59e0b" if ratio >= 0.8 else "#22c55e"
        x = 45 + index * 220
        blocks.append(
            f'<rect x="{x}" y="80" width="180" height="120" rx="16" fill="{color}"/>'
            f'<text x="{x + 90}" y="125" text-anchor="middle" font-family="Arial" font-size="20" fill="#fff">{html.escape(zone)}</text>'
            f'<text x="{x + 90}" y="170" text-anchor="middle" font-family="Arial" font-size="30" font-weight="700" fill="#fff">{count}/{capacity}</text>'
        )
    width = max(520, 90 + len(maximums) * 220)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="260"><rect width="100%" height="100%" fill="#fff"/><text x="45" y="40" font-family="Arial" font-size="24" font-weight="700">Ocupación máxima por zona</text>{"".join(blocks)}</svg>'


def run(input_dir: Path, output_dir: Path) -> dict[str, object]:
    payload = json.loads((input_dir / "detections.json").read_text(encoding="utf-8"))
    capacities = {key: int(value) for key, value in payload["zone_capacity"].items()}
    frames = payload["frames"]
    _validate_privacy(frames)
    maximums: dict[str, int] = defaultdict(int)
    timeline = []
    alerts = []
    for frame in frames:
        per_zone: dict[str, set[str]] = defaultdict(set)
        for detected in frame["objects"]:
            per_zone[detected["zone"]].add(str(detected["track_id"]))
        counts = {zone: len(tracks) for zone, tracks in per_zone.items()}
        for zone, count in counts.items():
            maximums[zone] = max(maximums[zone], count)
            if count > capacities[zone]:
                alerts.append({"timestamp": frame["timestamp"], "zone": zone, "count": count, "capacity": capacities[zone]})
        timeline.append({"timestamp": frame["timestamp"], "counts": counts})
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "privacy": {"biometrics_stored": False, "raw_video_retention": "disabled-in-local-demo"},
        "max_occupancy": dict(maximums),
        "timeline": timeline,
        "alerts": alerts,
    }
    (output_dir / "occupancy.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output_dir / "occupancy-heatmap.svg").write_text(
        _heatmap_svg(dict(maximums), capacities), encoding="utf-8"
    )
    return {
        "project": "visionops-multicloud",
        "status": "LOCAL_VERIFIED",
        "frames": len(frames),
        "zones": len(capacities),
        "alerts": len(alerts),
        "biometrics_stored": False,
    }
