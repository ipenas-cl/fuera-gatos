"""Detector guionado: devuelve detecciones predefinidas por cuadro (para simulación)."""
from __future__ import annotations

from collections.abc import Iterable, Iterator

import numpy as np

from .base import Detection


class ScriptedDetector:
    def __init__(self, script: Iterable[list[Detection]]):
        self._it: Iterator[list[Detection]] = iter(script)
        self.finished = False

    def detect(self, frame: np.ndarray) -> list[Detection]:
        try:
            return next(self._it)
        except StopIteration:
            self.finished = True
            return []
