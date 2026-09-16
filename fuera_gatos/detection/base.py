"""Tipos comunes para los detectores."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2 en píxeles
    zone: str | None = field(default=None)

    @property
    def anchor(self) -> tuple[float, float]:
        """Punto de apoyo del animal: centro del borde inferior del cuadro."""
        x1, _, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, float(y2))

    @property
    def area(self) -> int:
        x1, y1, x2, y2 = self.bbox
        return max(0, x2 - x1) * max(0, y2 - y1)


class Detector(Protocol):
    def detect(self, frame: np.ndarray) -> list[Detection]:
        ...
