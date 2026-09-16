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
    """Base con temporizador de apagado y tope duro de seguridad.

    Con `pulse_on_s`/`pulse_off_s` la salida se enciende y apaga en ráfagas
    mientras dura la activación (un chorro intermitente sorprende más que uno
    continuo y gasta la mitad de agua).
    """

    def __init__(self, name: str, max_on_s: float = 10.0,
                 pulse_on_s: float = 0.0, pulse_off_s: float = 0.0):
        self.name = name
        self.max_on_s = float(max_on_s)
        self.pulse_on_s = float(pulse_on_s)
        self.pulse_off_s = float(pulse_off_s)
        self._timer: threading.Timer | None = None
        self._lock = threading.RLock()
        self._generation = 0
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
            self._generation += 1
            self._timer = threading.Timer(duration, self.stop)
            self._timer.daemon = True
            self._timer.start()
            if self.pulse_on_s > 0 and self.pulse_off_s > 0:
                th = threading.Thread(target=self._pulse_loop, args=(self._generation,), daemon=True)
                th.start()

    def _pulse_loop(self, generation: int) -> None:
        import time

        on = True
        while True:
            time.sleep(self.pulse_on_s if on else self.pulse_off_s)
            with self._lock:
                if not self.active or generation != self._generation:
                    return
                try:
                    if on:
                        self._off()
                    else:
                        self._on()
                except Exception:
                    log.exception("Error en ráfaga de '%s'", self.name)
                    return
            on = not on

    def stop(self) -> None:
        with self._lock:
            self._cancel_timer()
            self._generation += 1  # detiene cualquier hilo de ráfagas
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
