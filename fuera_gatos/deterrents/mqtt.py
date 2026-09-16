"""Disuasores que viven en un nodo remoto (ESP32 con ESPHome) y se comandan por MQTT.

Convención ESPHome:
    <nodo>/switch/<nombre>/command     ON | OFF
    <nodo>/number/<nombre>/command     valor numérico (ángulo del servo)
El tope duro de tiempo se repite en el firmware del nodo (`on_turn_on: delay,
turn_off`), así que aunque se caiga la red la salida se apaga sola.
"""
from __future__ import annotations

import logging

from .base import TimedDeterrent
from .turret import AxisMap, WaterTurret

log = logging.getLogger(__name__)


class MqttSwitch(TimedDeterrent):
    def __init__(self, name: str, bus, topic: str, on_payload: str = "ON", off_payload: str = "OFF",
                 max_on_s: float = 10.0, pulse_on_s: float = 0.0, pulse_off_s: float = 0.0):
        super().__init__(name, max_on_s, pulse_on_s=pulse_on_s, pulse_off_s=pulse_off_s)
        self.bus, self.topic = bus, topic
        self.on_payload, self.off_payload = on_payload, off_payload

    def _on(self) -> None:
        self.bus.publish(self.topic, self.on_payload)
        log.info("MQTT '%s' -> %s %s", self.name, self.topic, self.on_payload)

    def _off(self) -> None:
        self.bus.publish(self.topic, self.off_payload)


class MqttServoDriver:
    """Publica el ángulo de cada canal en su tópico (canal = índice en `topics`)."""

    def __init__(self, bus, topics: list[str]):
        self.bus, self.topics = bus, list(topics)

    def set_angle(self, channel: int, degrees: float) -> None:
        self.bus.publish(self.topics[channel], f"{degrees:.1f}")

    def close(self) -> None:
        pass


class _MqttValve:
    def __init__(self, bus, topic: str, on_payload: str = "ON", off_payload: str = "OFF"):
        self.bus, self.topic, self.on_payload, self.off_payload = bus, topic, on_payload, off_payload

    def on(self) -> None:
        self.bus.publish(self.topic, self.on_payload)

    def off(self) -> None:
        self.bus.publish(self.topic, self.off_payload)


def build_mqtt_turret(name: str, bus, opts: dict, max_on: float, pulse: dict) -> WaterTurret:
    cal = opts.get("calibration") or {}
    if "pan" not in cal or "tilt" not in cal:
        raise ValueError(f"Torreta '{name}': falta calibration.pan / calibration.tilt")
    limits = opts.get("limits") or {}
    topics = opts.get("topics") or {}
    for key in ("pan", "tilt", "valve"):
        if key not in topics:
            raise ValueError(f"Torreta MQTT '{name}': falta topics.{key}")
    rest = opts.get("rest_angles")
    return WaterTurret(
        name,
        servo=MqttServoDriver(bus, [topics["pan"], topics["tilt"]]),
        pan_channel=0,
        tilt_channel=1,
        pan_map=AxisMap(cal["pan"], tuple(limits["pan"]) if "pan" in limits else None),
        tilt_map=AxisMap(cal["tilt"], tuple(limits["tilt"]) if "tilt" in limits else None),
        valve=_MqttValve(bus, topics["valve"]),
        lead_s=float(opts.get("lead_s", 0.3)),
        rest_angles=tuple(rest) if rest else None,
        max_on_s=max_on,
        **pulse,
    )
