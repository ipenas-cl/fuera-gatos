"""Registro de eventos (JSONL) y guardado de capturas."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np

from .config import EventsConfig
from .controller import Event

log = logging.getLogger(__name__)


def save_image(path: Path, frame: np.ndarray) -> Path:
    """Guarda como PNG/JPG si hay OpenCV; si no, como PPM (sin dependencias)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import cv2  # type: ignore

        bgr = frame[..., ::-1] if frame.ndim == 3 else frame
        cv2.imwrite(str(path), bgr)
        return path
    except ImportError:
        ppm = path.with_suffix(".ppm")
        h, w = frame.shape[:2]
        if frame.ndim == 2:
            frame = np.stack([frame] * 3, axis=-1)
        with ppm.open("wb") as fh:
            fh.write(f"P6 {w} {h} 255\n".encode())
            fh.write(np.ascontiguousarray(frame[..., :3], dtype=np.uint8).tobytes())
        return ppm


class EventLog:
    def __init__(self, cfg: EventsConfig):
        self.cfg = cfg
        self.log_path = Path(cfg.log_file)
        self.snap_dir = Path(cfg.snapshots_dir)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: Event, frame: np.ndarray | None = None) -> Path | None:
        data = event.to_dict()
        data["wall_time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        snapshot = None
        if self.cfg.save_snapshots and event.kind == "activated":
            name = time.strftime("%Y%m%d-%H%M%S") + f"-{event.level}.jpg"
            try:
                if self.cfg.snapshot_url:
                    snapshot = self._fetch_snapshot(self.snap_dir / name)
                elif frame is not None:
                    snapshot = save_image(self.snap_dir / name, frame)
                if snapshot:
                    data["snapshot"] = str(snapshot)
            except Exception:
                log.exception("No se pudo guardar la captura")
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False) + "\n")
        return snapshot

    def _fetch_snapshot(self, path: Path) -> Path | None:
        import urllib.request

        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(self.cfg.snapshot_url, timeout=5) as resp:
            path.write_bytes(resp.read())
        return path
