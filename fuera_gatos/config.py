"""Carga y validación de la configuración (YAML -> dataclasses)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    pass


@dataclass
class CameraConfig:
    source: str = "synthetic"
    device: Any = 0
    width: int = 640
    height: int = 480
    fps: float = 8.0
    rotate: int = 0


@dataclass
class MotionConfig:
    threshold: int = 25
    min_area: int = 1500
    max_area: int = 60000


@dataclass
class DetectorConfig:
    backend: str = "motion"
    model: str = "yolov8n.pt"
    camera: str = ""            # backend=frigate: nombre de la cámara en Frigate
    topic: str = "frigate/events"
    confidence: float = 0.45
    target_labels: list[str] = field(default_factory=lambda: ["cat"])
    suppress_labels: list[str] = field(default_factory=lambda: ["person", "dog"])
    motion: MotionConfig = field(default_factory=MotionConfig)


@dataclass
class ZoneConfig:
    name: str
    polygon: list[tuple[float, float]]
    # Disuasores permitidos en esta zona. None = todos los del nivel.
    # Útil para el techo compartido: luz y ultrasonido sí, agua nunca.
    deterrents: list[str] | None = None


@dataclass
class EscalationLevel:
    name: str
    deterrents: list[str]
    duration_s: float


@dataclass
class QuietHours:
    start: str = "22:00"
    end: str = "07:00"
    allowed: list[str] = field(default_factory=list)


@dataclass
class ControllerConfig:
    confirm_frames: int = 3
    confirm_window_s: float = 2.0
    cooldown_s: float = 30.0
    max_activations_per_hour: int = 12
    escalate_if_return_within_s: float = 300.0
    escalation: list[EscalationLevel] = field(
        default_factory=lambda: [EscalationLevel("nivel_1", ["luz", "sonido"], 4.0)]
    )
    quiet_hours: QuietHours | None = None


@dataclass
class DeterrentConfig:
    name: str
    type: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class SensorConfig:
    name: str
    type: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventsConfig:
    log_file: str = "data/events.jsonl"
    snapshots_dir: str = "data/snapshots"
    save_snapshots: bool = True
    snapshot_url: str = ""      # p. ej. http://frigate:5000/api/<camara>/latest.jpg


@dataclass
class MqttConfig:
    host: str = ""
    port: int = 1883
    username: str = ""
    password: str = ""
    client_id: str = "fuera-gatos"


@dataclass
class TelegramConfig:
    enabled: bool = False
    token: str = ""
    chat_id: str = ""


@dataclass
class NotifyConfig:
    telegram: TelegramConfig = field(default_factory=TelegramConfig)


@dataclass
class AppConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    zones: list[ZoneConfig] = field(default_factory=list)
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    deterrents: dict[str, DeterrentConfig] = field(default_factory=dict)
    sensors: dict[str, SensorConfig] = field(default_factory=dict)
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    events: EventsConfig = field(default_factory=EventsConfig)
    notify: NotifyConfig = field(default_factory=NotifyConfig)


def _sub(d: dict, key: str) -> dict:
    v = d.get(key) or {}
    if not isinstance(v, dict):
        raise ConfigError(f"'{key}' debe ser un mapa")
    return v


def _build(cls, data: dict, **overrides):
    """Construye un dataclass simple desde un dict, ignorando claves desconocidas."""
    fields = {f for f in cls.__dataclass_fields__}
    kwargs = {k: v for k, v in data.items() if k in fields}
    kwargs.update(overrides)
    return cls(**kwargs)


def config_from_dict(raw: dict) -> AppConfig:
    if not isinstance(raw, dict):
        raise ConfigError("La configuración debe ser un mapa YAML")

    camera = _build(CameraConfig, _sub(raw, "camera"))
    if camera.rotate not in (0, 90, 180, 270):
        raise ConfigError("camera.rotate debe ser 0, 90, 180 o 270")

    det_raw = _sub(raw, "detector")
    detector = _build(
        DetectorConfig, det_raw, motion=_build(MotionConfig, _sub(det_raw, "motion"))
    )
    if detector.backend not in ("yolo", "motion", "frigate"):
        raise ConfigError("detector.backend debe ser 'yolo', 'motion' o 'frigate'")
    if detector.backend == "frigate" and not detector.camera:
        raise ConfigError("detector.camera es obligatorio con backend=frigate")
    if not 0 < detector.confidence <= 1:
        raise ConfigError("detector.confidence debe estar entre 0 y 1")
    if not detector.target_labels:
        raise ConfigError("detector.target_labels no puede estar vacío")

    zones: list[ZoneConfig] = []
    for z in _sub(raw, "zones").get("include") or []:
        poly = [(float(p[0]), float(p[1])) for p in z.get("polygon", [])]
        if len(poly) < 3:
            raise ConfigError(f"La zona '{z.get('name')}' necesita al menos 3 puntos")
        allowed = z.get("deterrents")
        if allowed is not None:
            allowed = [str(a) for a in allowed]
        zones.append(ZoneConfig(name=str(z.get("name", f"zona{len(zones)+1}")), polygon=poly,
                                deterrents=allowed))

    ctrl_raw = _sub(raw, "controller")
    levels = [
        EscalationLevel(
            name=str(lv.get("name", f"nivel_{i+1}")),
            deterrents=list(lv.get("deterrents", [])),
            duration_s=float(lv.get("duration_s", 3)),
        )
        for i, lv in enumerate(ctrl_raw.get("escalation") or [])
    ]
    quiet = None
    if ctrl_raw.get("quiet_hours"):
        quiet = _build(QuietHours, ctrl_raw["quiet_hours"])
    ctrl_kwargs = {}
    if levels:
        ctrl_kwargs["escalation"] = levels
    controller = _build(ControllerConfig, ctrl_raw, quiet_hours=quiet, **ctrl_kwargs)
    if controller.confirm_frames < 1:
        raise ConfigError("controller.confirm_frames debe ser >= 1")
    for lv in controller.escalation:
        if lv.duration_s <= 0 or lv.duration_s > 30:
            raise ConfigError(
                f"Nivel '{lv.name}': duration_s debe estar entre 0 y 30 s (medida de seguridad)"
            )

    deterrents: dict[str, DeterrentConfig] = {}
    for name, d in _sub(raw, "deterrents").items():
        if not isinstance(d, dict) or "type" not in d:
            raise ConfigError(f"Disuasor '{name}' necesita un campo 'type'")
        opts = {k: v for k, v in d.items() if k != "type"}
        deterrents[name] = DeterrentConfig(name=name, type=str(d["type"]), options=opts)

    for lv in controller.escalation:
        for dname in lv.deterrents:
            if dname not in deterrents:
                raise ConfigError(
                    f"Nivel '{lv.name}' usa el disuasor '{dname}' que no está definido"
                )

    for z in zones:
        for dname in z.deterrents or []:
            if dname not in deterrents:
                raise ConfigError(f"Zona '{z.name}' permite el disuasor '{dname}' que no está definido")

    sensors: dict[str, SensorConfig] = {}
    for name, d in _sub(raw, "sensors").items():
        if not isinstance(d, dict) or "type" not in d:
            raise ConfigError(f"Sensor '{name}' necesita un campo 'type'")
        opts = {k: v for k, v in d.items() if k != "type"}
        for g in opts.get("gates", []):
            if g not in deterrents:
                raise ConfigError(f"Sensor '{name}' custodia el disuasor '{g}' que no está definido")
        sensors[name] = SensorConfig(name=name, type=str(d["type"]), options=opts)

    events = _build(EventsConfig, _sub(raw, "events"))
    mqtt = _build(MqttConfig, _sub(raw, "mqtt"))
    needs_mqtt = detector.backend == "frigate" or any(
        d.type.startswith("mqtt") for d in deterrents.values()
    ) or any(sn.type.startswith("mqtt") for sn in sensors.values())
    if needs_mqtt and not mqtt.host:
        raise ConfigError("Se usa Frigate o nodos MQTT pero falta mqtt.host")
    notify_raw = _sub(raw, "notify")
    notify = NotifyConfig(telegram=_build(TelegramConfig, _sub(notify_raw, "telegram")))

    return AppConfig(
        camera=camera,
        detector=detector,
        zones=zones,
        controller=controller,
        deterrents=deterrents,
        sensors=sensors,
        mqtt=mqtt,
        events=events,
        notify=notify,
    )


def load_config(path: str | Path) -> AppConfig:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"No existe el archivo de configuración: {p}")
    with p.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return config_from_dict(raw)
