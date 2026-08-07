from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]


def mermaid(nodes: list[str]) -> str:
    rows = ["flowchart LR"]
    for index, label in enumerate(nodes):
        rows.append(f'    N{index}["{label}"]')
    for index in range(len(nodes) - 1):
        rows.append(f"    N{index} --> N{index + 1}")
    rows.extend(["    classDef title fill:#0f172a,color:#f8fafc,stroke:#38bdf8", "    class N0 title"])
    return "\n".join(rows) + "\n"


def svg(title: str, nodes: list[str]) -> str:
    width = max(920, len(nodes) * 190)
    boxes: list[str] = []
    arrows: list[str] = []
    for index, label in enumerate(nodes):
        x = 35 + index * 185
        fill = "#0f172a" if index == 0 else "#e0f2fe"
        foreground = "#f8fafc" if index == 0 else "#0f172a"
        boxes.append(
            f'<rect x="{x}" y="100" width="155" height="74" rx="12" fill="{fill}" stroke="#0284c7" stroke-width="2"/>'
            f'<text x="{x + 77.5}" y="137" text-anchor="middle" dominant-baseline="middle" fill="{foreground}" font-size="13">{html.escape(label)}</text>'
        )
        if index:
            arrows.append(f'<path d="M {x - 30} 137 L {x - 5} 137" stroke="#0284c7" stroke-width="3" marker-end="url(#arrow)"/>')
    return dedent(
        f'''\
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="230" viewBox="0 0 {width} 230" role="img" aria-labelledby="title desc">
          <title id="title">{html.escape(title)}</title>
          <desc id="desc">Flujo arquitectónico de izquierda a derecha.</desc>
          <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#0284c7"/></marker></defs>
          <rect width="100%" height="100%" fill="#ffffff"/>
          <text x="35" y="48" fill="#0f172a" font-family="Arial, sans-serif" font-size="22" font-weight="700">{html.escape(title)}</text>
          <g font-family="Arial, sans-serif">{''.join(arrows)}{''.join(boxes)}</g>
        </svg>'''
    ).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if committed diagrams are stale")
    args = parser.parse_args()
    descriptor = json.loads((ROOT / "diagrams/architecture.json").read_text(encoding="utf-8"))
    stale: list[str] = []
    for name, nodes in descriptor["flows"].items():
        expected = {
            ROOT / f"diagrams/src/{name}.mmd": mermaid(nodes),
            ROOT / f"diagrams/rendered/{name}.svg": svg(f"{descriptor['title']} · {name.upper()}", nodes),
        }
        for path, content in expected.items():
            if args.check:
                if not path.exists() or path.read_text(encoding="utf-8") != content:
                    stale.append(str(path.relative_to(ROOT)))
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        raise SystemExit("stale diagrams: " + ", ".join(stale))
    print("diagram sources and SVG exports are consistent")


if __name__ == "__main__":
    main()
