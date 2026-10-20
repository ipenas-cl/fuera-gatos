"""Configuración del panel de casa (casa.yaml)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..config import ConfigError, MqttConfig, NotifyConfig, TelegramConfig, _build, _sub


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    token: str = ""             # clave de acceso al panel; vacía = sin clave (solo red local)


@dataclass
class CasaCamera:
    name: str                   # igual al nombre de la cámara en Frigate
    title: str = ""


@dataclass
class DoorbellConfig:
    camera: str = ""            # cámara de Frigate del timbre; una persona en ella avisa como visita
    ring_topic: str = ""        # tópico MQTT que publica el timbre al pulsarlo
    ring_payload: str = ""      # si se indica, solo ese contenido cuenta como pulsación
    answer_topic: str = ""      # opcional: tópico para abrir/hablar desde el panel
    open_topic: str = ""        # opcional: tópico que abre la puerta
    open_payload: str = "ON"


@dataclass
class SwitchConfig:
    name: str
    title: str = ""
    command_topic: str = ""
    state_topic: str = ""
    on: str = "ON"
    off: str = "OFF"


@dataclass
class CasaConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    frigate_url: str = "http://localhost:5000"
    cameras: list[CasaCamera] = field(default_factory=list)
    doorbell: DoorbellConfig = field(default_factory=DoorbellConfig)
    switches: list[SwitchConfig] = field(default_factory=list)
    labels: list[str] = field(default_factory=lambda: ["person", "cat", "dog", "package"])
    notify_labels: list[str] = field(default_factory=lambda: ["person"])
    mqtt: MqttConfig = field(default_factory=lambda: MqttConfig(client_id="fuera-gatos-casa"))
    notify: NotifyConfig = field(default_factory=NotifyConfig)


def casa_from_dict(raw: dict) -> CasaConfig:
    if not isinstance(raw, dict):
        raise ConfigError("casa.yaml debe ser un mapa")
    cameras = []
    for c in raw.get("cameras") or []:
        if not isinstance(c, dict) or not c.get("name"):
            raise ConfigError("cada cámara necesita 'name'")
        cameras.append(_build(CasaCamera, c, title=c.get("title") or c["name"]))
    switches = []
    for s in raw.get("switches") or []:
        if not isinstance(s, dict) or not s.get("name") or not s.get("command_topic"):
            raise ConfigError("cada interruptor necesita 'name' y 'command_topic'")
        switches.append(_build(SwitchConfig, s, title=s.get("title") or s["name"]))
    names = [c.name for c in cameras]
    doorbell = _build(DoorbellConfig, _sub(raw, "doorbell"))
    if doorbell.camera and doorbell.camera not in names:
        raise ConfigError(f"doorbell.camera '{doorbell.camera}' no está en cameras")
    mqtt = _build(MqttConfig, _sub(raw, "mqtt"), client_id=_sub(raw, "mqtt").get("client_id", "fuera-gatos-casa"))
    notify_raw = _sub(raw, "notify")
    cfg = CasaConfig(
        server=_build(ServerConfig, _sub(raw, "server")),
        frigate_url=str(_sub(raw, "frigate").get("url", "http://localhost:5000")).rstrip("/"),
        cameras=cameras,
        doorbell=doorbell,
        switches=switches,
        mqtt=mqtt,
        notify=NotifyConfig(telegram=_build(TelegramConfig, _sub(notify_raw, "telegram"))),
    )
    if "labels" in raw:
        cfg.labels = list(raw["labels"])
    if "notify_labels" in raw:
        cfg.notify_labels = list(raw["notify_labels"])
    needs_mqtt = bool(switches or doorbell.ring_topic or doorbell.open_topic)
    if needs_mqtt and not mqtt.host:
        raise ConfigError("Hay interruptores o timbre por MQTT pero falta mqtt.host")
    return cfg


def load_casa(path: str | Path) -> CasaConfig:
    with open(path, encoding="utf-8") as f:
        return casa_from_dict(yaml.safe_load(f) or {})
