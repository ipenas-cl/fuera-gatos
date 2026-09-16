"""Disuasores por relé (GPIO): luz, electroválvula del aspersor, módulo ultrasónico."""
from __future__ import annotations

import logging

from .base import TimedDeterrent

log = logging.getLogger(__name__)


class RelayDeterrent(TimedDeterrent):
    def __init__(self, name: str, pin: int, active_high: bool = True, max_on_s: float = 10.0,
                 pulse_on_s: float = 0.0, pulse_off_s: float = 0.0):
        super().__init__(name, max_on_s, pulse_on_s=pulse_on_s, pulse_off_s=pulse_off_s)
        self.pin = int(pin)
        try:
            from gpiozero import OutputDevice  # type: ignore
        except ImportError as exc:  # pragma: no cover - depende del hardware
            raise RuntimeError(
                "Falta 'gpiozero'. Instalar con: pip install 'fuera-gatos[gpio]' "
                "(o usar --simulate para probar sin hardware)"
            ) from exc
        self._device = OutputDevice(self.pin, active_high=active_high, initial_value=False)

    def _on(self) -> None:
        self._device.on()
        log.info("Relé '%s' (GPIO%d) ENCENDIDO", self.name, self.pin)

    def _off(self) -> None:
        self._device.off()
        log.info("Relé '%s' (GPIO%d) apagado", self.name, self.pin)

    def close(self) -> None:
        super().close()
        try:
            self._device.close()
        except Exception:  # pragma: no cover
            pass
