from __future__ import annotations

import argparse
import base64
import html
import json
import shutil
import struct
import subprocess
import tempfile
import time
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIDTH = 1920
HEIGHT = 1080
NODE_WIDTH = 216
NODE_HEIGHT = 150


def _lines(value: str | list[str]) -> list[str]:
    return value if isinstance(value, list) else [value]


def _wrapped(value: str | list[str], width: int, maximum: int) -> list[str]:
    result: list[str] = []
    for original in _lines(value):
        result.extend(textwrap.wrap(str(original), width=width, break_long_words=False) or [""])
    return result[:maximum]


def _node_mermaid(node: dict[str, object]) -> str:
    text = "<br/>".join([*_lines(node["label"]), *_lines(node.get("detail", []))])
    shape = node.get("kind", "service")
    if shape == "actor":
        return f'    {node["id"]}(["{text}"])'
    if shape in {"database", "object_store"}:
        return f'    {node["id"]}[("{text}")]'
    if shape in {"queue", "event_bus"}:
        return f'    {node["id"]}{{{{"{text}"}}}}'
    if shape in {"failure", "review"}:
        return f'    {node["id"]}>"{text}"]'
    return f'    {node["id"]}["{text}"]'


def mermaid(view: dict[str, object]) -> str:
    rows = ["flowchart LR"]
    nodes = {node["id"]: node for node in view["nodes"]}
    assigned: set[str] = set()
    for group in view["groups"]:
        rows.append(f'  subgraph {group["id"]}["{group["title"]}"]')
        rows.append("    direction TB")
        for node in view["nodes"]:
            if node.get("group") == group["id"]:
                rows.append(_node_mermaid(node))
                assigned.add(str(node["id"]))
        rows.append("  end")
    for node_id, node in nodes.items():
        if node_id not in assigned:
            rows.append(_node_mermaid(node))
    for edge in view["edges"]:
        connector = "-.->" if edge.get("style") == "dashed" else "-->"
        rows.append(f'  {edge["from"]} {connector}|"{edge["label"]}"| {edge["to"]}')
    rows.extend(
        [
            "  classDef implemented fill:#dcfce7,stroke:#15803d,color:#052e16,stroke-width:2px",
            "  classDef planned fill:#fef3c7,stroke:#b45309,color:#451a03,stroke-width:2px",
            "  classDef external fill:#f1f5f9,stroke:#475569,color:#0f172a,stroke-width:2px",
            "  classDef local fill:#dbeafe,stroke:#1d4ed8,color:#172554,stroke-width:2px",
            "  classDef failure fill:#fee2e2,stroke:#b91c1c,color:#450a0a,stroke-width:2px",
        ]
    )
    for status in ["IMPLEMENTED", "PLANNED", "EXTERNAL", "LOCAL"]:
        members = [str(node["id"]) for node in view["nodes"] if node.get("status") == status]
        if members:
            rows.append(f"  class {','.join(members)} {status.lower()}")
    failures = [str(node["id"]) for node in view["nodes"] if node.get("kind") in {"failure", "review"}]
    if failures:
        rows.append(f"  class {','.join(failures)} failure")
    return "\n".join(rows) + "\n"


def _icon_data(node: dict[str, object]) -> str | None:
    icon = node.get("icon")
    if not icon:
        return None
    path = ROOT / str(icon)
    if not path.exists():
        raise FileNotFoundError(f"missing architecture icon: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _generic_icon(node: dict[str, object], x: float, y: float) -> str:
    kind = str(node.get("kind", "service"))
    color = {
        "actor": "#334155",
        "api": "#2563eb",
        "queue": "#7c3aed",
        "event_bus": "#7c3aed",
        "database": "#ca8a04",
        "object_store": "#ca8a04",
        "failure": "#dc2626",
        "review": "#dc2626",
        "monitor": "#0891b2",
        "security": "#059669",
    }.get(kind, "#2563eb")
    symbol = {
        "actor": "USER",
        "api": "API",
        "queue": "QUEUE",
        "event_bus": "EVENT",
        "database": "DB",
        "object_store": "DATA",
        "failure": "DLQ",
        "review": "HITL",
        "monitor": "SLO",
        "security": "IAM",
    }.get(kind, "APP")
    return (
        f'<circle cx="{x + 34}" cy="{y + 34}" r="30" fill="{color}" opacity="0.12"/>'
        f'<circle cx="{x + 34}" cy="{y + 34}" r="23" fill="none" stroke="{color}" stroke-width="3"/>'
        f'<text x="{x + 34}" y="{y + 38}" text-anchor="middle" font-size="11" font-weight="700" fill="{color}">{symbol}</text>'
    )


def _badge(status: str, x: float, y: float) -> str:
    colors = {
        "IMPLEMENTED": ("#dcfce7", "#166534"),
        "PLANNED": ("#fef3c7", "#92400e"),
        "EXTERNAL": ("#e2e8f0", "#334155"),
        "LOCAL": ("#dbeafe", "#1e40af"),
        "ACCESS_VARIABLE": ("#fce7f3", "#9d174d"),
    }
    fill, foreground = colors.get(status, colors["PLANNED"])
    width = max(62, len(status) * 6.2 + 15)
    return (
        f'<rect x="{x - width}" y="{y}" width="{width}" height="21" rx="10" fill="{fill}"/>'
        f'<text x="{x - width / 2}" y="{y + 14}" text-anchor="middle" font-size="9" font-weight="700" fill="{foreground}">{html.escape(status)}</text>'
    )


def _node_svg(node: dict[str, object]) -> str:
    x, y = float(node["x"]), float(node["y"])
    status = str(node.get("status", "PLANNED"))
    border = "#94a3b8"
    if node.get("kind") in {"failure", "review"}:
        border = "#ef4444"
    parts = [
        f'<g id="node-{html.escape(str(node["id"]))}">',
        f'<rect x="{x}" y="{y}" width="{NODE_WIDTH}" height="{NODE_HEIGHT}" rx="14" fill="#ffffff" stroke="{border}" stroke-width="2" filter="url(#shadow)"/>',
        _badge(status, x + NODE_WIDTH - 8, y + 7),
    ]
    icon_data = _icon_data(node)
    if icon_data:
        parts.append(f'<image href="{icon_data}" x="{x + 12}" y="{y + 35}" width="62" height="62" preserveAspectRatio="xMidYMid meet"/>')
    else:
        parts.append(_generic_icon(node, x + 12, y + 35))
    label_lines = _wrapped(node["label"], 19, 3)
    detail_lines = _wrapped(node.get("detail", []), 34, 3)
    text_x = x + 75
    label_y = y + 49
    for index, line in enumerate(label_lines[:3]):
        parts.append(f'<text x="{text_x}" y="{label_y + index * 15}" font-size="12" font-weight="700" fill="#0f172a">{html.escape(str(line))}</text>')
    detail_y = max(y + 108, label_y + len(label_lines[:3]) * 15 + 7)
    for index, line in enumerate(detail_lines[:3]):
        parts.append(f'<text x="{x + 12}" y="{detail_y + index * 13}" font-size="9.5" fill="#475569">{html.escape(str(line))}</text>')
    parts.append("</g>")
    return "".join(parts)


def _edge_points(source: dict[str, object], target: dict[str, object]) -> tuple[float, float, float, float]:
    sx, sy = float(source["x"]), float(source["y"])
    tx, ty = float(target["x"]), float(target["y"])
    if tx >= sx + NODE_WIDTH:
        return sx + NODE_WIDTH, sy + NODE_HEIGHT / 2, tx, ty + NODE_HEIGHT / 2
    if tx + NODE_WIDTH <= sx:
        return sx, sy + NODE_HEIGHT / 2, tx + NODE_WIDTH, ty + NODE_HEIGHT / 2
    if ty >= sy:
        return sx + NODE_WIDTH / 2, sy + NODE_HEIGHT, tx + NODE_WIDTH / 2, ty
    return sx + NODE_WIDTH / 2, sy, tx + NODE_WIDTH / 2, ty + NODE_HEIGHT


def _edge_svg(edge: dict[str, object], nodes: dict[str, dict[str, object]]) -> tuple[str, str]:
    source, target = nodes[str(edge["from"])], nodes[str(edge["to"])]
    sx, sy, tx, ty = _edge_points(source, target)
    if abs(tx - sx) > abs(ty - sy):
        middle = (sx + tx) / 2
        path = f"M {sx} {sy} H {middle} V {ty} H {tx}"
        label_x, label_y = middle, min(sy, ty) + abs(ty - sy) / 2 - 8
    else:
        middle = (sy + ty) / 2
        path = f"M {sx} {sy} V {middle} H {tx} V {ty}"
        label_x, label_y = min(sx, tx) + abs(tx - sx) / 2, middle - 8
    dashed = ' stroke-dasharray="8 7"' if edge.get("style") == "dashed" else ""
    color = "#64748b" if edge.get("style") == "dashed" else "#334155"
    label = html.escape(str(edge["label"]))
    path_svg = f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"{dashed} marker-end="url(#arrow)"/>'
    label_svg = f'<text x="{label_x}" y="{label_y}" text-anchor="middle" font-size="11" font-weight="600" fill="#334155" stroke="#ffffff" stroke-width="5" paint-order="stroke">{label}</text>'
    return path_svg, label_svg


def svg(view: dict[str, object], portfolio_title: str) -> str:
    nodes = {str(node["id"]): node for node in view["nodes"]}
    group_parts = []
    for group in view["groups"]:
        group_parts.append(
            f'<rect x="{group["x"]}" y="{group["y"]}" width="{group["width"]}" height="{group["height"]}" rx="18" fill="{group["color"]}" fill-opacity="0.52" stroke="#94a3b8" stroke-width="1.5"/>'
            f'<text x="{float(group["x"]) + 15}" y="{float(group["y"]) + 27}" font-size="15" font-weight="700" fill="#334155">{html.escape(str(group["title"]))}</text>'
        )
    edge_parts = [_edge_svg(edge, nodes) for edge in view["edges"]]
    edge_paths = "".join(part[0] for part in edge_parts)
    edge_labels = "".join(part[1] for part in edge_parts)
    cards = "".join(_node_svg(node) for node in view["nodes"])
    subtitle = html.escape(str(view.get("subtitle", "")))
    scale = html.escape(str(view.get("scale", "")))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">{html.escape(portfolio_title)} · {html.escape(str(view["name"]))}</title>
<desc id="desc">{subtitle}</desc>
<defs>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#0f172a" flood-opacity="0.14"/></filter>
  <marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L0,9 L8,4.5 z" fill="#334155"/></marker>
</defs>
<rect width="100%" height="100%" fill="#f8fafc"/>
<text x="48" y="48" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#0f172a">{html.escape(portfolio_title)} · {html.escape(str(view["name"]))}</text>
<text x="48" y="78" font-family="Arial, sans-serif" font-size="15" fill="#475569">{subtitle}</text>
<g font-family="Arial, sans-serif">{''.join(group_parts)}{edge_paths}{cards}{edge_labels}</g>
<rect x="48" y="1003" width="1824" height="48" rx="12" fill="#e2e8f0"/>
<text x="68" y="1033" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#0f172a">Escala/SLO: {scale}</text>
<g font-family="Arial, sans-serif" font-size="11"><rect x="1320" y="1016" width="14" height="14" rx="4" fill="#dcfce7"/><text x="1340" y="1028">IMPLEMENTED</text><rect x="1435" y="1016" width="14" height="14" rx="4" fill="#fef3c7"/><text x="1455" y="1028">PLANNED</text><rect x="1545" y="1016" width="14" height="14" rx="4" fill="#e2e8f0"/><text x="1565" y="1028">EXTERNAL</text><rect x="1655" y="1016" width="14" height="14" rx="4" fill="#dbeafe"/><text x="1675" y="1028">LOCAL</text></g>
</svg>\n'''


def _chrome() -> str | None:
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chrome"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    return next((candidate for candidate in candidates if candidate and Path(candidate).exists()), None)


def _render_png(svg_path: Path, png_path: Path) -> None:
    browser = _chrome()
    if not browser:
        raise RuntimeError("Chrome/Chromium is required only when regenerating PNG exports")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="portfolio-diagram-")
    if png_path.exists():
        png_path.unlink()
    command = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--allow-file-access-from-files",
        f"--user-data-dir={profile}",
        f"--window-size={WIDTH},{HEIGHT}",
        f"--screenshot={png_path.resolve()}",
        svg_path.resolve().as_uri(),
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if png_path.exists() and png_path.stat().st_size > 1_000:
                time.sleep(0.25)
                return
            if process.poll() is not None and process.returncode not in (0, None):
                break
            time.sleep(0.2)
    finally:
        if process.poll() is None:
            process.kill()
    raise RuntimeError(f"browser did not export PNG: {png_path}")


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", data[16:24])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if Mermaid/SVG/PNG are missing or stale")
    parser.add_argument("--render-png", action="store_true", help="Regenerate PNG exports using headless Chrome")
    parser.add_argument("--view", choices=["local", "portable", "aws", "gcp", "azure"], help="Process one architecture view")
    args = parser.parse_args()
    descriptor = json.loads((ROOT / "diagrams/architecture.json").read_text(encoding="utf-8"))
    stale: list[str] = []
    for view_name, view in descriptor["views"].items():
        if args.view and view_name != args.view:
            continue
        view["name"] = view_name.upper()
        expected_mmd = mermaid(view)
        expected_svg = svg(view, descriptor["title"])
        mmd_path = ROOT / f"diagrams/src/{view_name}.mmd"
        svg_path = ROOT / f"diagrams/rendered/{view_name}.svg"
        png_path = ROOT / f"diagrams/rendered/{view_name}.png"
        if args.check:
            if not mmd_path.exists() or mmd_path.read_text(encoding="utf-8") != expected_mmd:
                stale.append(str(mmd_path.relative_to(ROOT)))
            if not svg_path.exists() or svg_path.read_text(encoding="utf-8") != expected_svg:
                stale.append(str(svg_path.relative_to(ROOT)))
            if not png_path.exists() or _png_dimensions(png_path) != (WIDTH, HEIGHT):
                stale.append(str(png_path.relative_to(ROOT)))
        else:
            mmd_path.parent.mkdir(parents=True, exist_ok=True)
            svg_path.parent.mkdir(parents=True, exist_ok=True)
            mmd_path.write_text(expected_mmd, encoding="utf-8", newline="\n")
            svg_path.write_text(expected_svg, encoding="utf-8", newline="\n")
            if args.render_png:
                _render_png(svg_path, png_path)
    if stale:
        raise SystemExit("stale architecture artifacts: " + ", ".join(stale))
    print("detailed Mermaid, SVG and PNG architecture artifacts are consistent")


if __name__ == "__main__":
    main()
