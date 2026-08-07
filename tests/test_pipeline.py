import json
from pathlib import Path

import pytest

from visionops.pipeline import _validate_privacy, run


def test_counts_occupancy_and_capacity_alerts(tmp_path: Path) -> None:
    summary = run(Path("data/sample"), tmp_path)
    report = json.loads((tmp_path / "occupancy.json").read_text(encoding="utf-8"))
    assert summary["frames"] == 3
    assert summary["alerts"] == 1
    assert report["max_occupancy"]["checkout"] == 3
    assert report["privacy"]["biometrics_stored"] is False
    assert (tmp_path / "occupancy-heatmap.svg").exists()


def test_rejects_identifying_fields() -> None:
    with pytest.raises(ValueError, match="forbidden"):
        _validate_privacy([{"objects": [{"track_id": "anonymous-1", "zone": "entry", "name": "person"}]}])
