"""Prueba de extremo a extremo con cámara sintética, detector de movimiento y disuasores simulados."""
import json

from fuera_gatos.config import config_from_dict
from fuera_gatos.pipeline import run


def test_end_to_end_synthetic(tmp_path):
    raw = {
        "camera": {"source": "synthetic", "width": 320, "height": 240, "fps": 200},
        "detector": {"backend": "motion", "target_labels": ["cat"],
                     "motion": {"threshold": 25, "min_area": 800, "max_area": 30000}},
        "zones": {"include": [{"name": "jardin", "polygon": [[0, 120], [320, 120], [320, 240], [0, 240]]}]},
        "controller": {"confirm_frames": 3, "confirm_window_s": 5, "cooldown_s": 1,
                       "escalation": [{"name": "n1", "deterrents": ["luz"], "duration_s": 0.2}]},
        "deterrents": {"luz": {"type": "log", "max_on_s": 1}},
        "events": {"log_file": str(tmp_path / "events.jsonl"),
                   "snapshots_dir": str(tmp_path / "snaps"), "save_snapshots": True},
    }
    cfg = config_from_dict(raw)
    assert run(cfg, simulate=True, max_frames=80) == 0
    lines = [json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()]
    kinds = [l["kind"] for l in lines]
    assert "activated" in kinds
    act = next(l for l in lines if l["kind"] == "activated")
    assert act["deterrents"] == ["luz"]
    assert act["detections"][0]["zone"] == "jardin"
    assert list((tmp_path / "snaps").iterdir())
