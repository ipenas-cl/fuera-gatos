"""Detector por diferencia de cuadros (sin red neuronal).

Sirve como respaldo en equipos muy modestos (Pi Zero). No distingue un gato de
otro bulto del mismo tamaño, así que conviene combinarlo con zonas acotadas y
con los límites de área (min_area/max_area).
"""
from __future__ import annotations

from collections import deque

import numpy as np

from .base import Detection


def to_gray(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 2:
        return frame.astype(np.float32)
    return (
        0.299 * frame[..., 0] + 0.587 * frame[..., 1] + 0.114 * frame[..., 2]
    ).astype(np.float32)


def _box_blur(img: np.ndarray, k: int = 5) -> np.ndarray:
    if k <= 1:
        return img
    pad = k // 2
    padded = np.pad(img, pad, mode="edge")
    c = np.cumsum(np.cumsum(padded, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = img.shape
    total = c[k : k + h, k : k + w] - c[:h, k : k + w] - c[k : k + h, :w] + c[:h, :w]
    return total / float(k * k)


def _blobs(mask: np.ndarray, cell: int = 8) -> list[tuple[int, int, int, int, int]]:
    """Agrupa la máscara en celdas y devuelve cajas (x1,y1,x2,y2,area_px)."""
    h, w = mask.shape
    gh, gw = (h + cell - 1) // cell, (w + cell - 1) // cell
    grid = np.zeros((gh, gw), dtype=np.int32)
    for gy in range(gh):
        for gx in range(gw):
            block = mask[gy * cell : (gy + 1) * cell, gx * cell : (gx + 1) * cell]
            grid[gy, gx] = int(block.sum())
    occupied = grid > (cell * cell) // 4
    seen = np.zeros_like(occupied)
    out = []
    for gy in range(gh):
        for gx in range(gw):
            if not occupied[gy, gx] or seen[gy, gx]:
                continue
            stack = [(gy, gx)]
            seen[gy, gx] = True
            ys, xs, area = [], [], 0
            while stack:
                cy, cx = stack.pop()
                ys.append(cy)
                xs.append(cx)
                area += int(grid[cy, cx])
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < gh and 0 <= nx < gw and occupied[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            out.append(
                (
                    min(xs) * cell,
                    min(ys) * cell,
                    min(w, (max(xs) + 1) * cell),
                    min(h, (max(ys) + 1) * cell),
                    area,
                )
            )
    return out


class MotionDetector:
    def __init__(
        self,
        threshold: int = 25,
        min_area: int = 1500,
        max_area: int = 60000,
        label: str = "cat",
        learn_rate: float = 0.05,
        warmup_frames: int = 5,
    ):
        self.threshold = float(threshold)
        self.min_area = int(min_area)
        self.max_area = int(max_area)
        self.label = label
        self.learn_rate = float(learn_rate)
        self.warmup_frames = int(warmup_frames)
        self._background: np.ndarray | None = None
        self._frames_seen = 0
        self._recent = deque(maxlen=3)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        gray = _box_blur(to_gray(frame), 5)
        self._frames_seen += 1
        if self._background is None:
            self._background = gray.copy()
            return []
        diff = np.abs(gray - self._background)
        mask = diff > self.threshold
        # El fondo aprende despacio para absorber cambios de luz, no al gato.
        self._background += self.learn_rate * (gray - self._background)
        if self._frames_seen <= self.warmup_frames:
            return []
        dets = []
        for x1, y1, x2, y2, area in _blobs(mask):
            if self.min_area <= area <= self.max_area:
                conf = min(1.0, area / float(self.max_area) + 0.5)
                dets.append(Detection(self.label, round(conf, 3), (x1, y1, x2, y2)))
        return dets
