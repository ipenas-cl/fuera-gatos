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
        if simulate:
            out[name] = LogDeterrent(name, max_on_s=max_on)
            continue
        if cfg.type == "relay":
            from .relay import RelayDeterrent

            out[name] = RelayDeterrent(
                name,
                pin=int(cfg.options["pin"]),
                active_high=bool(cfg.options.get("active_high", True)),
                max_on_s=max_on,
            )
        elif cfg.type == "sound":
            from .sound import SoundDeterrent

            out[name] = SoundDeterrent(
                name,
                files=list(cfg.options.get("files", [])),
                player=str(cfg.options.get("player", "aplay")),
                max_on_s=max_on,
            )
        elif cfg.type == "log":
            out[name] = LogDeterrent(name, max_on_s=max_on)
        else:
            raise ValueError(f"Tipo de disuasor desconocido: '{cfg.type}' en '{name}'")
    return out
