"""Torreta de agua: chorro fino que sigue al gato con dos servos (pan/tilt).

El controlador llama a `aim(x, y, ts)` con la posición del gato en píxeles en
cada cuadro, antes y durante la activación. La torreta convierte píxeles a
grados con una calibración lineal de dos puntos por eje, anticipa el movimiento
(`lead_s`) y respeta límites mecánicos para no apuntar nunca fuera del terreno.
La válvula o bomba va por un relé y hereda el tope duro y las ráfagas.
"""
from __future__ import annotations

import logging

from .base import TimedDeterrent
from .servo import ServoDriver

log = logging.getLogger(__name__)


class AxisMap:
    """Mapa lineal píxel -> grados a partir de dos puntos [[px, deg], [px, deg]]."""

    def __init__(self, points: list[list[float]], limits: tuple[float, float] | None = None):
        if len(points) != 2 or points[0][0] == points[1][0]:
            raise ValueError("La calibración de cada eje necesita dos puntos con píxel distinto")
        (p0, d0), (p1, d1) = points
        self._slope = (d1 - d0) / (p1 - p0)
        self._offset = d0 - self._slope * p0
        lo, hi = limits if limits else (0.0, 180.0)
        self.limits = (min(lo, hi), max(lo, hi))

    def __call__(self, px: float) -> float:
        deg = self._slope * px + self._offset
        return max(self.limits[0], min(self.limits[1], deg))


class WaterTurret(TimedDeterrent):
    def __init__(
        self,
        name: str,
        servo: ServoDriver,
        pan_channel: int,
        tilt_channel: int,
        pan_map: AxisMap,
        tilt_map: AxisMap,
        valve=None,  # objeto con .on()/.off() (relé); None en simulación
        lead_s: float = 0.3,
        rest_angles: tuple[float, float] | None = None,
        max_on_s: float = 6.0,
        pulse_on_s: float = 0.0,
        pulse_off_s: float = 0.0,
        min_step_deg: float = 0.5,
    ):
        super().__init__(name, max_on_s, pulse_on_s=pulse_on_s, pulse_off_s=pulse_off_s)
        self.servo = servo
        self.pan_channel, self.tilt_channel = pan_channel, tilt_channel
        self.pan_map, self.tilt_map = pan_map, tilt_map
        self.valve = valve
        self.lead_s = float(lead_s)
        self.rest_angles = rest_angles
        self.min_step_deg = float(min_step_deg)
        self._last: tuple[float, float, float] | None = None  # x, y, ts
        self._angles: tuple[float, float] | None = None
        self.aimed_at: tuple[float, float] | None = None
        if rest_angles:
            self._move(*rest_angles)

    # --- puntería -------------------------------------------------------
    def aim(self, x: float, y: float, ts: float) -> tuple[float, float]:
        """Apunta al píxel (x, y) anticipando el movimiento. Devuelve (pan, tilt)."""
        tx, ty = x, y
        if self._last is not None:
            lx, ly, lt = self._last
            dt = ts - lt
            if 0 < dt < 1.0 and self.lead_s > 0:
                tx = x + (x - lx) / dt * self.lead_s
                ty = y + (y - ly) / dt * self.lead_s
        self._last = (x, y, ts)
        self.aimed_at = (tx, ty)
        pan, tilt = self.pan_map(tx), self.tilt_map(ty)
        self._move(pan, tilt)
        return pan, tilt

    def _move(self, pan: float, tilt: float) -> None:
        if self._angles is not None:
            if abs(pan - self._angles[0]) < self.min_step_deg and abs(tilt - self._angles[1]) < self.min_step_deg:
                return
        self.servo.set_angle(self.pan_channel, pan)
        self.servo.set_angle(self.tilt_channel, tilt)
        self._angles = (pan, tilt)

    def forget_target(self) -> None:
        self._last = None

    # --- válvula --------------------------------------------------------
    def _on(self) -> None:
        if self.valve is not None:
            self.valve.on()
        log.info("Torreta '%s': AGUA (pan=%.0f° tilt=%.0f°)", self.name,
                 *(self._angles or (0.0, 0.0)))

    def _off(self) -> None:
        if self.valve is not None:
            self.valve.off()
        log.info("Torreta '%s': agua cerrada", self.name)

    def stop(self) -> None:
        super().stop()
        self._last = None

    def close(self) -> None:
        super().close()
        if self.rest_angles:
            self._move(*self.rest_angles)
        try:
            self.servo.close()
        except Exception:  # pragma: no cover
            pass
        if self.valve is not None and hasattr(self.valve, "close"):
            self.valve.close()
