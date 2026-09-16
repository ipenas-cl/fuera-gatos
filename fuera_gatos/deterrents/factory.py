"""Construye los disuasores a partir de la configuración."""
from __future__ import annotations

import logging

from ..config import DeterrentConfig
from .base import Deterrent
from .simulated import LogDeterrent

log = logging.getLogger(__name__)


def build_deterrents(configs: dict[str, DeterrentConfig], simulate: bool = False) -> dict[str, Deterrent]:
    out: dict[str, Deterrent] = {}
    for name, cfg in configs.items():
        max_on = float(cfg.options.get("max_on_s", 10.0))
        pulse = dict(
            pulse_on_s=float(cfg.options.get("pulse_on_s", 0.0)),
            pulse_off_s=float(cfg.options.get("pulse_off_s", 0.0)),
        )
        if simulate:
            if cfg.type == "turret":
                out[name] = _build_turret(name, cfg.options, max_on, pulse, simulate=True)
            else:
                out[name] = LogDeterrent(name, max_on_s=max_on, **pulse)
            continue
        if cfg.type == "relay":
            from .relay import RelayDeterrent

            out[name] = RelayDeterrent(
                name,
                pin=int(cfg.options["pin"]),
                active_high=bool(cfg.options.get("active_high", True)),
                max_on_s=max_on,
                **pulse,
            )
        elif cfg.type == "sound":
            from .sound import SoundDeterrent

            out[name] = SoundDeterrent(
                name,
                files=list(cfg.options.get("files", [])),
                player=str(cfg.options.get("player", "aplay")),
                max_on_s=max_on,
            )
        elif cfg.type == "turret":
            out[name] = _build_turret(name, cfg.options, max_on, pulse, simulate=False)
        elif cfg.type == "log":
            out[name] = LogDeterrent(name, max_on_s=max_on, **pulse)
        else:
            raise ValueError(f"Tipo de disuasor desconocido: '{cfg.type}' en '{name}'")
    return out


def _build_turret(name: str, opts: dict, max_on: float, pulse: dict, simulate: bool):
    from .servo import build_servo_driver
    from .turret import AxisMap, WaterTurret

    servo_opts = dict(opts.get("servo") or {})
    cal = opts.get("calibration") or {}
    if "pan" not in cal or "tilt" not in cal:
        raise ValueError(f"Torreta '{name}': falta calibration.pan / calibration.tilt")
    limits = opts.get("limits") or {}
    pan_map = AxisMap(cal["pan"], tuple(limits["pan"]) if "pan" in limits else None)
    tilt_map = AxisMap(cal["tilt"], tuple(limits["tilt"]) if "tilt" in limits else None)

    valve = None
    if not simulate:
        from gpiozero import OutputDevice  # type: ignore

        valve = OutputDevice(int(opts["valve_pin"]), active_high=bool(opts.get("active_high", True)),
                             initial_value=False)
    rest = opts.get("rest_angles")
    return WaterTurret(
        name,
        servo=build_servo_driver(servo_opts, simulate=simulate),
        pan_channel=int(servo_opts.get("pan_channel", servo_opts.get("pan_pin", 0))),
        tilt_channel=int(servo_opts.get("tilt_channel", servo_opts.get("tilt_pin", 1))),
        pan_map=pan_map,
        tilt_map=tilt_map,
        valve=valve,
        lead_s=float(opts.get("lead_s", 0.3)),
        rest_angles=tuple(rest) if rest else None,
        max_on_s=max_on,
        **pulse,
    )
