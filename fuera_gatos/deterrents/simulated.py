"""Disuasor que solo registra lo que haría. Útil en pruebas y simulación."""
from __future__ import annotations

import logging

from .base import TimedDeterrent

log = logging.getLogger(__name__)


class LogDeterrent(TimedDeterrent):
    def __init__(self, name: str, max_on_s: float = 10.0, use_timer: bool = True):
        super().__init__(name, max_on_s)
        self.use_timer = use_timer
        self.calls: list[tuple[str, float]] = []

    def start(self, duration_s: float) -> None:
        duration = min(float(duration_s), self.max_on_s)
        self.calls.append(("start", duration))
        if self.use_timer:
            super().start(duration)
        else:
            self._on()
            self.active = True

    def stop(self) -> None:
        if self.active:
            self.calls.append(("stop", 0.0))
        if self.use_timer:
            super().stop()
        else:
            if self.active:
                self._off()
            self.active = False

    def _on(self) -> None:
        log.info("[SIM] %s ENCENDIDO", self.name)

    def _off(self) -> None:
        log.info("[SIM] %s apagado", self.name)
