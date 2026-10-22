"""Tests with the camera, the YOLO model and the network mocked out (no hardware or downloads)."""
import json
import sys
import types
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest

from fuera_gatos.config import NotifyConfig, TelegramConfig, config_from_dict
from fuera_gatos.detection.base import Detection
from fuera_gatos.notify import Notifier
from fuera_gatos.pipeline import run, split_detections


class _Tensor(list):
    def tolist(self):
        return list(self)


class _Box:
    def __init__(self, cls, conf, xyxy):
        self.cls, self.conf, self.xyxy = [cls], [conf], [_Tensor(xyxy)]


class _FakeYOLO:
    names: ClassVar[dict] = {0: "person", 15: "cat", 16: "dog"}
    last_kwargs: ClassVar[dict] = {}

    def __init__(self, model):
        self.model = model

    def predict(self, frame, **kwargs):
        _FakeYOLO.last_kwargs = kwargs
        return [types.SimpleNamespace(boxes=[_Box(15, 0.91234, [10.0, 20.0, 110.0, 140.0])]),
                types.SimpleNamespace(boxes=None)]


@pytest.fixture
def fake_ultralytics(monkeypatch):
    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=_FakeYOLO))


def test_yolo_detector_maps_boxes_and_restricts_classes(fake_ultralytics):
    from fuera_gatos.detection.yolo import YoloDetector

    det = YoloDetector(model="yolov8n.pt", confidence=0.5, classes=["cat", "person"])
    out = det.detect(np.zeros((240, 320, 3), dtype=np.uint8))
    assert out == [Detection("cat", 0.912, (10, 20, 110, 140))]
    assert sorted(_FakeYOLO.last_kwargs["classes"]) == [0, 15]
    assert _FakeYOLO.last_kwargs["conf"] == 0.5


def test_yolo_detector_explains_missing_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "ultralytics", None)
    from fuera_gatos.detection.yolo import YoloDetector

    with pytest.raises(RuntimeError, match="ultralytics"):
        YoloDetector()


class FakeCamera:
    """Yields a dropped frame first, then N blank frames."""

    def __init__(self, n):
        self.frames = [None] + [np.zeros((240, 320, 3), dtype=np.uint8)] * n
        self.closed = False

    def read(self):
        return self.frames.pop(0) if self.frames else np.zeros((240, 320, 3), dtype=np.uint8)

    def close(self):
        self.closed = True


class FakeDetector:
    def __init__(self, script):
        self.script = list(script)

    def detect(self, frame):
        return self.script.pop(0) if self.script else []


def _cfg(tmp_path):
    return config_from_dict({
        "camera": {"source": "none", "width": 320, "height": 240, "fps": 500},
        "detector": {"backend": "motion", "target_labels": ["cat"], "suppress_labels": ["person"]},
        "zones": {"include": [{"name": "basura", "polygon": [[0, 0], [320, 0], [320, 240], [0, 240]]}]},
        "controller": {"confirm_frames": 2, "confirm_window_s": 5, "cooldown_s": 60,
                       "escalation": [{"name": "n1", "deterrents": ["luz"], "duration_s": 0.1}]},
        "deterrents": {"luz": {"type": "log", "max_on_s": 1}},
        "events": {"log_file": str(tmp_path / "events.jsonl"), "snapshots_dir": str(tmp_path / "s"),
                   "save_snapshots": False},
    })


def _events(tmp_path):
    p = tmp_path / "events.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def test_pipeline_with_mocked_camera_and_model(tmp_path, monkeypatch):
    monkeypatch.setattr("fuera_gatos.pipeline.time.sleep", lambda s: None)
    cat = Detection("cat", 0.9, (100, 100, 160, 200))
    cam = FakeCamera(4)
    assert run(_cfg(tmp_path), simulate=True, max_frames=4, camera=cam, detector=FakeDetector([[cat]] * 4)) == 0
    acts = [e for e in _events(tmp_path) if e["kind"] == "activated"]
    assert len(acts) == 1, "cooldown must prevent a second activation"
    assert acts[0]["detections"][0]["zone"] == "basura"
    assert cam.closed


def test_pipeline_never_acts_when_a_person_is_present(tmp_path, monkeypatch):
    monkeypatch.setattr("fuera_gatos.pipeline.time.sleep", lambda s: None)
    frame = [Detection("cat", 0.9, (100, 100, 160, 200)), Detection("person", 0.8, (0, 0, 50, 230))]
    run(_cfg(tmp_path), simulate=True, max_frames=4, camera=FakeCamera(4), detector=FakeDetector([frame] * 4))
    assert not [e for e in _events(tmp_path) if e["kind"] == "activated"]


def test_split_detections_filters_targets_by_zone_but_keeps_suppressors(tmp_path):
    cfg = config_from_dict({
        "detector": {"backend": "motion", "target_labels": ["cat"], "suppress_labels": ["person"]},
        "zones": {"include": [{"name": "z", "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]}]},
        "controller": {"escalation": [{"name": "n1", "deterrents": ["luz"], "duration_s": 1}]},
        "deterrents": {"luz": {"type": "log"}},
    })
    inside = Detection("cat", 0.9, (10, 10, 50, 50))
    outside = Detection("cat", 0.9, (200, 200, 250, 250))
    person = Detection("person", 0.9, (200, 200, 250, 250))
    out = split_detections(cfg, [inside, outside, person])
    assert [d.label for d in out] == ["cat", "person"]
    assert out[0].zone == "z"


class _Resp:
    def read(self):
        return b"{}"


def test_notifier_disabled_without_credentials():
    assert not Notifier(NotifyConfig(TelegramConfig(enabled=True, token="", chat_id="1"))).enabled


def test_notifier_sends_text_and_photo(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("fuera_gatos.notify.urllib.request.urlopen", lambda req, timeout: calls.append(req) or _Resp())
    n = Notifier(NotifyConfig(TelegramConfig(enabled=True, token="T", chat_id="42")))
    n._send("hola", None)
    photo = Path(tmp_path / "snap.jpg")
    photo.write_bytes(b"\xff\xd8jpeg")
    n._send("gato", photo)
    assert calls[0].full_url.endswith("/botT/sendMessage")
    assert json.loads(calls[0].data) == {"chat_id": "42", "text": "hola"}
    assert calls[1].full_url.endswith("/botT/sendPhoto")
    assert b"jpeg" in calls[1].data and b'name="caption"' in calls[1].data


def test_notifier_swallows_network_errors(monkeypatch):
    def boom(req, timeout):
        raise OSError("offline")

    monkeypatch.setattr("fuera_gatos.notify.urllib.request.urlopen", boom)
    Notifier(NotifyConfig(TelegramConfig(enabled=True, token="T", chat_id="42")))._send("x", None)
