"""Fuentes de video: cámara de la Pi, USB/RTSP (OpenCV) o sintética."""
from __future__ import annotations

import logging
import time

import numpy as np

from .config import CameraConfig

log = logging.getLogger(__name__)


class Camera:
    def read(self) -> np.ndarray | None:  # RGB uint8 (H, W, 3)
        raise NotImplementedError

    def close(self) -> None:
        pass


def _rotate(frame: np.ndarray, deg: int) -> np.ndarray:
    if deg == 90:
        return np.rot90(frame, -1)
    if deg == 180:
        return np.rot90(frame, 2)
    if deg == 270:
        return np.rot90(frame, 1)
    return frame


class PiCamera(Camera):
    def __init__(self, cfg: CameraConfig):
        try:
            from picamera2 import Picamera2  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Falta picamera2: sudo apt install -y python3-picamera2") from exc
        self.cfg = cfg
        self._cam = Picamera2()
        conf = self._cam.create_video_configuration(
            main={"size": (cfg.width, cfg.height), "format": "RGB888"}
        )
        self._cam.configure(conf)
        self._cam.start()
        time.sleep(1.0)  # exposición inicial

    def read(self) -> np.ndarray | None:
        frame = self._cam.capture_array()
        return _rotate(frame, self.cfg.rotate)

    def close(self) -> None:
        self._cam.stop()


class OpenCVCamera(Camera):
    def __init__(self, cfg: CameraConfig):
        try:
            import cv2  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Falta OpenCV: pip install 'fuera-gatos[opencv]'") from exc
        self._cv2 = cv2
        self.cfg = cfg
        self._cap = cv2.VideoCapture(cfg.device)
        if not self._cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara: {cfg.device!r}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)

    def read(self) -> np.ndarray | None:
        ok, bgr = self._cap.read()
        if not ok:
            return None
        return _rotate(bgr[..., ::-1], self.cfg.rotate)

    def close(self) -> None:
        self._cap.release()


class SyntheticCamera(Camera):
    """Genera un fondo con ruido y un 'bulto' que aparece, se mueve y se va.

    Sirve para probar el detector de movimiento sin hardware.
    """

    def __init__(self, cfg: CameraConfig, cat_frames: tuple[int, int] = (15, 60), seed: int = 0):
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        self.frame_idx = 0
        self.cat_frames = cat_frames
        base = np.full((cfg.height, cfg.width, 3), 90, dtype=np.uint8)
        base[cfg.height // 2 :, :, 1] += 40  # "pasto"
        self._base = base

    def read(self) -> np.ndarray | None:
        frame = self._base.copy()
        noise = self.rng.integers(-3, 4, size=frame.shape, dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        start, end = self.cat_frames
        if start <= self.frame_idx < end:
            t = (self.frame_idx - start) / max(1, end - start)
            cx = int(self.cfg.width * (0.2 + 0.6 * t))
            cy = int(self.cfg.height * 0.75)
            w, h = 70, 45
            frame[cy - h // 2 : cy + h // 2, cx - w // 2 : cx + w // 2] = (40, 35, 30)
        self.frame_idx += 1
        return frame


class NullCamera(Camera):
    """Sin video local (el detector es Frigate). Devuelve un cuadro vacío para marcar el ritmo."""

    def __init__(self, cfg: CameraConfig):
        self._frame = np.zeros((max(1, cfg.height), max(1, cfg.width), 3), dtype=np.uint8)

    def read(self) -> np.ndarray | None:
        return self._frame


def open_camera(cfg: CameraConfig) -> Camera:
    if cfg.source == "none":
        return NullCamera(cfg)
    if cfg.source == "picamera":
        return PiCamera(cfg)
    if cfg.source in ("usb", "rtsp"):
        return OpenCVCamera(cfg)
    if cfg.source == "synthetic":
        return SyntheticCamera(cfg)
    raise ValueError(f"Fuente de cámara desconocida: {cfg.source}")
