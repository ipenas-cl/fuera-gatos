"""Arranque del panel: MQTT + hub + servidor HTTP."""
from __future__ import annotations

import logging

from ..notify import Notifier
from .config import CasaConfig
from .hub import Hub
from .server import CasaServer

log = logging.getLogger(__name__)


def build_notify(cfg: CasaConfig, frigate_get):
    """Telegram con la captura actual de la cámara; sin Telegram no hace nada."""
    notifier = Notifier(cfg.notify)
    if not notifier.enabled:
        return None

    def notify(text: str, camera: str) -> None:
        import tempfile
        from pathlib import Path

        photo = None
        try:
            with frigate_get(f"api/{camera}/latest.jpg", timeout=5) as r:
                tmp = Path(tempfile.mkdtemp()) / "captura.jpg"
                tmp.write_bytes(r.read())
                photo = tmp
        except Exception as exc:
            log.debug("sin captura para el aviso: %s", exc)
        notifier.send(text, photo)

    return notify


def run_casa(cfg: CasaConfig, simulate: bool = False) -> int:
    bus = None
    if cfg.mqtt.host:
        if simulate:
            from ..mqtt import FakeBus

            bus = FakeBus()
        else:
            from ..mqtt import MqttBus

            bus = MqttBus(cfg.mqtt.host, cfg.mqtt.port, cfg.mqtt.username or None,
                          cfg.mqtt.password or None, cfg.mqtt.client_id)
    app = CasaServer(cfg, hub=None)
    app.hub = Hub(cfg, bus, notify=build_notify(cfg, app.frigate_get))
    httpd = app.make_httpd()
    log.info("Panel de casa en http://%s:%s (Frigate: %s)", cfg.server.host, cfg.server.port, cfg.frigate_url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        if bus is not None:
            bus.close()
    return 0
