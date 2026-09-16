"""Bucle principal: cámara -> detector -> zonas -> controlador -> eventos."""
from __future__ import annotations

import logging
import signal
import time

from .camera import open_camera
from .config import AppConfig
from .controller import Controller, Event
from .detection.motion import MotionDetector
from .deterrents import build_deterrents
from .events import EventLog
from .notify import Notifier
from .sensors import build_sensors, guards_from_sensors
from .zones import assign_zones

log = logging.getLogger(__name__)


def build_bus(cfg: AppConfig, simulate: bool = False):
    """Cliente MQTT si la configuración lo necesita; FakeBus en simulación."""
    d = cfg.detector
    needed = d.backend == "frigate" or any(x.type.startswith("mqtt") for x in cfg.deterrents.values()) \
        or any(x.type.startswith("mqtt") for x in cfg.sensors.values())
    if not needed:
        return None
    if simulate:
        from .mqtt import FakeBus

        return FakeBus()
    from .mqtt import MqttBus

    return MqttBus(cfg.mqtt.host, cfg.mqtt.port, cfg.mqtt.username or None,
                   cfg.mqtt.password or None, cfg.mqtt.client_id)


def build_detector(cfg: AppConfig, bus=None):
    d = cfg.detector
    if d.backend == "frigate":
        from .detection.frigate import FrigateDetector

        return FrigateDetector(bus, camera=d.camera, topic=d.topic, min_score=d.confidence)
    if d.backend == "yolo":
        from .detection.yolo import YoloDetector

        return YoloDetector(
            model=d.model,
            confidence=d.confidence,
            classes=sorted(set(d.target_labels) | set(d.suppress_labels)),
        )
    return MotionDetector(
        threshold=d.motion.threshold,
        min_area=d.motion.min_area,
        max_area=d.motion.max_area,
        label=d.target_labels[0],
    )


def split_detections(cfg: AppConfig, raw):
    """Separa objetivos (filtrados por zona) de etiquetas de supresión (todo el cuadro)."""
    suppress = [d for d in raw if d.label in cfg.detector.suppress_labels]
    targets = assign_zones([d for d in raw if d.label in cfg.detector.target_labels], cfg.zones)
    return targets + suppress


def run(cfg: AppConfig, simulate: bool = False, max_frames: int | None = None,
        detector=None, camera=None, bus=None) -> int:
    bus = bus or build_bus(cfg, simulate=simulate)
    deterrents = build_deterrents(cfg.deterrents, simulate=simulate, bus=bus)
    sensors = build_sensors(cfg.sensors, simulate=simulate, bus=bus)
    event_log = EventLog(cfg.events)
    notifier = Notifier(cfg.notify)
    latest = {"frame": None}

    def on_event(ev: Event) -> None:
        snap = event_log.record(ev, latest["frame"])
        if ev.kind == "activated":
            zones = sorted({d.zone for d in ev.detections if d.zone})
            log.warning("GATO en %s -> %s (%s)", ", ".join(zones) or "?", ", ".join(ev.deterrents), ev.level)
            notifier.send(
                f"Gato detectado en {', '.join(zones)}. Activado: {', '.join(ev.deterrents)} ({ev.level})",
                snap,
            )
        elif ev.kind == "resource_empty":
            log.warning("%s", ev.reason)
            notifier.send(f"Atención: {ev.reason}. Hay que rellenar el estanque.")
        elif ev.kind in ("suppressed", "rate_limited"):
            log.info("Sin acción: %s", ev.reason)

    controller = Controller(
        cfg.controller,
        deterrents,
        target_labels=cfg.detector.target_labels,
        suppress_labels=cfg.detector.suppress_labels,
        on_event=on_event,
        zone_deterrents={z.name: z.deterrents for z in cfg.zones},
        guards=guards_from_sensors(sensors),
    )
    detector = detector or build_detector(cfg, bus)
    camera = camera or open_camera(cfg.camera)

    stop = {"flag": False}

    def _sig(*_):
        stop["flag"] = True

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    period = 1.0 / max(0.5, cfg.camera.fps)
    frames = 0
    log.info("fuera-gatos iniciado (detector=%s, cámara=%s, simulación=%s)",
             cfg.detector.backend, cfg.camera.source, simulate)
    try:
        while not stop["flag"]:
            t0 = time.monotonic()
            frame = camera.read()
            if frame is None:
                log.warning("Cámara sin cuadro; reintentando")
                controller.tick()
                time.sleep(1.0)
                continue
            latest["frame"] = frame
            controller.process(split_detections(cfg, detector.detect(frame)))
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
            elapsed = time.monotonic() - t0
            if elapsed < period:
                time.sleep(period - elapsed)
    finally:
        controller.close()
        for sensor in sensors.values():
            sensor.close()
        camera.close()
        if bus is not None:
            bus.close()
        log.info("fuera-gatos detenido tras %d cuadros", frames)
    return 0
