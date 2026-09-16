"""Sensores de entrada: por ahora, interruptor de flotador para el nivel del estanque.

Un sensor "custodia" uno o más disuasores: cuando dice que no hay recurso
(estanque vacío), el controlador no los activa y avisa una sola vez.
"""
from __future__ import annotations

import logging
from typing import Callable, Protocol

from .config import SensorConfig

log = logging.getLogger(__name__)


class Sensor(Protocol):
    name: str
    gates: list[str]

    def ok(self) -> bool: ...

    def close(self) -> None: ...


class FloatSwitch:
    """Flotador en un pin con pull-up interno. `empty_when` indica qué nivel lógico
    corresponde a estanque vacío ("low" = el flotador cierra a masa cuando hay agua)."""

    def __init__(self, name: str, pin: int, empty_when: str = "low", gates: list[str] | None = None):
        try:
            from gpiozero import Button  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Falta 'gpiozero'. Instalar con: pip install 'fuera-gatos[gpio]'") from exc
        if empty_when not in ("low", "high"):
            raise ValueError("empty_when debe ser 'low' o 'high'")
        self.name = name
        self.gates = list(gates or [])
        self._empty_when_low = empty_when == "low"
        # Button con pull_up=True: is_pressed == True cuando el pin está a masa (low).
        self._dev = Button(int(pin), pull_up=True, bounce_time=0.2)

    def ok(self) -> bool:
        low = bool(self._dev.is_pressed)
        empty = low if self._empty_when_low else not low
        return not empty

    def close(self) -> None:
        try:
            self._dev.close()
        except Exception:  # pragma: no cover
            pass


class SimulatedSensor:
    def __init__(self, name: str, gates: list[str] | None = None, state: bool = True):
        self.name = name
        self.gates = list(gates or [])
        self.state = state

    def ok(self) -> bool:
        return self.state

    def close(self) -> None:
        pass


def build_sensors(configs: dict[str, SensorConfig], simulate: bool = False) -> dict[str, Sensor]:
    out: dict[str, Sensor] = {}
    for name, cfg in configs.items():
        gates = [str(g) for g in cfg.options.get("gates", [])]
        if simulate or cfg.type == "log":
            out[name] = SimulatedSensor(name, gates=gates)
        elif cfg.type == "float_switch":
            out[name] = FloatSwitch(name, pin=int(cfg.options["pin"]),
                                    empty_when=str(cfg.options.get("empty_when", "low")), gates=gates)
        else:
            raise ValueError(f"Tipo de sensor desconocido: '{cfg.type}' en '{name}'")
    return out


def guards_from_sensors(sensors: dict[str, Sensor]) -> dict[str, Callable[[], bool]]:
    """Mapa disuasor -> función que dice si está disponible (todos sus sensores en ok)."""
    by_deterrent: dict[str, list[Sensor]] = {}
    for s in sensors.values():
        for g in s.gates:
            by_deterrent.setdefault(g, []).append(s)

    def make(sens: list[Sensor]) -> Callable[[], bool]:
        return lambda: all(x.ok() for x in sens)

    return {d: make(sens) for d, sens in by_deterrent.items()}
