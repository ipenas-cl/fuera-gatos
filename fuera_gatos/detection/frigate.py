"""Detector que no procesa imágenes: lee los objetos que Frigate ya reconoció.

Frigate publica en MQTT `frigate/events` un JSON por cada objeto seguido
(type: new | update | end) con `after.camera`, `after.label`, `after.box`
[x1, y1, x2, y2] en píxeles de la resolución de detección y `after.score`.
Este detector mantiene la lista de objetos vivos de UNA cámara y la devuelve
en cada llamada a `detect()`; el cuadro se ignora.
"""
from __future__ import annotations

import json
import logging
import threading
import time

import numpy as np

from .base import Detection

log = logging.getLogger(__name__)


class FrigateDetector:
    def __init__(self, bus, camera: str, topic: str = "frigate/events", stale_s: float = 3.0,
                 min_score: float = 0.0):
        self.bus = bus
        self.camera = camera
        self.stale_s = float(stale_s)
        self.min_score = float(min_score)
        self._objects: dict[str, tuple[Detection, float]] = {}
        self._lock = threading.Lock()
        bus.subscribe(topic, self._on_event)

    def _on_event(self, topic: str, payload: bytes) -> None:
        try:
            ev = json.loads(payload)
        except ValueError:
            return
        self.ingest(ev)

    def ingest(self, ev: dict, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        kind = ev.get("type")
        after = ev.get("after") or {}
        if after.get("camera") != self.camera:
            return
        oid = str(after.get("id"))
        with self._lock:
            if kind == "end" or after.get("false_positive"):
                self._objects.pop(oid, None)
                return
            box = after.get("box")
            if not box or len(box) != 4:
                return
            score = float(after.get("score") or after.get("top_score") or 0.0)
            if score < self.min_score:
                self._objects.pop(oid, None)
                return
            det = Detection(str(after.get("label")), round(score, 3), tuple(int(v) for v in box))
            self._objects[oid] = (det, now)

    def detect(self, frame: np.ndarray | None = None) -> list[Detection]:
        now = time.monotonic()
        with self._lock:
            stale = [k for k, (_, ts) in self._objects.items() if now - ts > self.stale_s]
            for k in stale:
                del self._objects[k]
            return [Detection(d.label, d.confidence, d.bbox) for d, _ in self._objects.values()]
