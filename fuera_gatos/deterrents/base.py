"""Interfaz común de los disuasores.

Regla de oro: todo disuasor se apaga solo. `start(duration_s)` programa su
propio apagado y `max_on_s` es un tope duro que no depende del controlador,
para que un fallo de software nunca deje la electroválvula abierta.
"""
from __future__ import annotations

import logging
import threading
from typing import Protocol

log = logging.getLogger(__name__)


class Deterrent(Protocol):
    name: str

    def start(self, duration_s: float) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


class TimedDeterrent:
    """Base con temporizador de apagado y tope duro de seguridad."""

    def __init__(self, name: str, max_on_s: float = 10.0):
        self.name = name
        self.max_on_s = float(max_on_s)
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self.active = False

    # Implementar en subclases
    def _on(self) -> None:
        raise NotImplementedError

    def _off(self) -> None:
        raise NotImplementedError

    def start(self, duration_s: float) -> None:
        duration = min(float(duration_s), self.max_on_s)
        if duration <= 0:
            return
        with self._lock:
            self._cancel_timer()
            try:
                self._on()
                self.active = True
            except Exception:
                log.exception("No se pudo activar '%s'", self.name)
                return
            self._timer = threading.Timer(duration, self.stop)
            self._timer.daemon = True
            self._timer.start()

    def stop(self) -> None:
        with self._lock:
            self._cancel_timer()
            if not self.active:
                return
            try:
                self._off()
            finally:
                self.active = False

    def close(self) -> None:
        self.stop()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
