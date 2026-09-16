"""Controladores de servo para la torreta: gpiozero (PWM directo), PCA9685 (I2C) o simulado."""
from __future__ import annotations

import logging
from typing import Protocol

log = logging.getLogger(__name__)


class ServoDriver(Protocol):
    def set_angle(self, channel: int, degrees: float) -> None: ...

    def close(self) -> None: ...


class LogServoDriver:
    """Solo registra los ángulos (simulación y pruebas)."""

    def __init__(self) -> None:
        self.angles: dict[int, float] = {}
        self.history: list[tuple[int, float]] = []

    def set_angle(self, channel: int, degrees: float) -> None:
        self.angles[channel] = degrees
        self.history.append((channel, degrees))
        log.debug("[SIM] servo %d -> %.1f°", channel, degrees)

    def close(self) -> None:
        pass


class GpiozeroServoDriver:
    """Servos conectados directo a pines PWM de la Pi (canal = número de pin BCM).

    Con la fábrica de pines por defecto el PWM por software tiembla; conviene
    instalar pigpio y arrancar con GPIOZERO_PIN_FACTORY=pigpio.
    """

    def __init__(self, min_pulse_ms: float = 0.5, max_pulse_ms: float = 2.5):
        try:
            from gpiozero import AngularServo  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Falta 'gpiozero'. Instalar con: pip install 'fuera-gatos[gpio]'") from exc
        self._cls = AngularServo
        self._kw = dict(min_angle=0, max_angle=180,
                        min_pulse_width=min_pulse_ms / 1000, max_pulse_width=max_pulse_ms / 1000)
        self._servos: dict[int, object] = {}

    def set_angle(self, channel: int, degrees: float) -> None:
        if channel not in self._servos:
            self._servos[channel] = self._cls(channel, **self._kw)
        self._servos[channel].angle = max(0.0, min(180.0, degrees))  # type: ignore[attr-defined]

    def close(self) -> None:
        for s in self._servos.values():
            try:
                s.close()  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover
                pass


class PCA9685ServoDriver:
    """Módulo PCA9685 por I2C (16 canales, PWM por hardware, sin temblor)."""

    _MODE1 = 0x00
    _PRESCALE = 0xFE
    _LED0_ON_L = 0x06

    def __init__(self, address: int = 0x40, bus: int = 1, freq_hz: int = 50,
                 min_pulse_ms: float = 0.5, max_pulse_ms: float = 2.5):
        try:
            from smbus2 import SMBus  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Falta 'smbus2' para el PCA9685: pip install smbus2") from exc
        self._bus = SMBus(bus)
        self._addr = address
        self._min_ms, self._max_ms = min_pulse_ms, max_pulse_ms
        self._period_ms = 1000.0 / freq_hz
        prescale = int(round(25_000_000 / (4096 * freq_hz)) - 1)
        self._bus.write_byte_data(self._addr, self._MODE1, 0x10)  # sleep
        self._bus.write_byte_data(self._addr, self._PRESCALE, prescale)
        self._bus.write_byte_data(self._addr, self._MODE1, 0x20)  # auto-increment, despierto

    def set_angle(self, channel: int, degrees: float) -> None:
        degrees = max(0.0, min(180.0, degrees))
        pulse_ms = self._min_ms + (self._max_ms - self._min_ms) * degrees / 180.0
        ticks = int(4096 * pulse_ms / self._period_ms)
        reg = self._LED0_ON_L + 4 * channel
        self._bus.write_i2c_block_data(self._addr, reg, [0, 0, ticks & 0xFF, ticks >> 8])

    def close(self) -> None:
        try:
            self._bus.close()
        except Exception:  # pragma: no cover
            pass


def build_servo_driver(opts: dict, simulate: bool = False) -> ServoDriver:
    driver = str(opts.get("driver", "gpiozero"))
    if simulate or driver == "log":
        return LogServoDriver()
    if driver == "gpiozero":
        return GpiozeroServoDriver(float(opts.get("min_pulse_ms", 0.5)), float(opts.get("max_pulse_ms", 2.5)))
    if driver == "pca9685":
        return PCA9685ServoDriver(
            address=int(opts.get("address", 0x40)), bus=int(opts.get("bus", 1)),
            freq_hz=int(opts.get("freq_hz", 50)),
            min_pulse_ms=float(opts.get("min_pulse_ms", 0.5)), max_pulse_ms=float(opts.get("max_pulse_ms", 2.5)),
        )
    raise ValueError(f"Driver de servo desconocido: {driver}")
