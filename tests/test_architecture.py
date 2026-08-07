from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLOUDS = {"aws", "gcp", "azure"}
EXPECTED_VIEWS = {"local", "portable", *CLOUDS}


def _descriptor() -> dict[str, object]:
    return json.loads((ROOT / "diagrams/architecture.json").read_text(encoding="utf-8"))


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def test_all_detailed_views_have_sources_and_exports() -> None:
    views = _descriptor()["views"]
    assert set(views) == EXPECTED_VIEWS
    for name, view in views.items():
        assert len(view["nodes"]) >= 12, name
        assert len(view["edges"]) >= 12, name
        assert len(view["groups"]) >= 6, name
        assert view["scale"], name
        assert (ROOT / f"diagrams/src/{name}.mmd").exists()
        assert (ROOT / f"diagrams/rendered/{name}.svg").exists()
        png = ROOT / f"diagrams/rendered/{name}.png"
        assert png.exists()
        assert _png_dimensions(png) == (1920, 1080)


def test_edges_and_required_operational_paths_are_valid() -> None:
    for name, view in _descriptor()["views"].items():
        nodes = {node["id"]: node for node in view["nodes"]}
        assert len(nodes) == len(view["nodes"]), f"duplicate node id in {name}"
        for edge in view["edges"]:
            assert edge["from"] in nodes
            assert edge["to"] in nodes
            assert edge["label"]
        kinds = {node.get("kind") for node in view["nodes"]}
        assert {"actor", "api", "failure", "monitor", "security"} <= kinds
        assert {"database", "object_store"} & kinds


def test_cloud_services_have_official_icons_and_terraform_traceability() -> None:
    views = _descriptor()["views"]
    for cloud in CLOUDS:
        terraform = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / f"infra/{cloud}").glob("*.tf"))
        managed = [node for node in views[cloud]["nodes"] if node["status"] not in {"EXTERNAL", "LOCAL"}]
        assert len(managed) >= 9
        for node in managed:
            icon = ROOT / node["icon"]
            assert icon.exists() and icon.suffix == ".svg", (cloud, node["id"])
            assert node.get("terraform"), (cloud, node["id"])
            if node["status"] == "IMPLEMENTED":
                assert node["terraform"] in terraform, (cloud, node["id"], node["terraform"])


def test_readme_embeds_png_and_links_mermaid_sources() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for view in EXPECTED_VIEWS:
        assert f"diagrams/rendered/{view}.png" in readme
        assert f"diagrams/src/{view}.mmd" in readme
