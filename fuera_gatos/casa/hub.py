"""Hub de eventos en vivo: MQTT (Frigate, timbre, interruptores) -> clientes del panel (SSE)."""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Callable

from .config import CasaConfig

log = logging.getLogger(__name__)


class Hub:
    def __init__(self, cfg: CasaConfig, bus, notify: Callable[[str, str], None] | None = None,
                 clock: Callable[[], float] = time.time):
        self.cfg = cfg
        self.bus = bus
        self._notify = notify
        self._clock = clock
        self._clients: list[queue.Queue] = []
        self._lock = threading.Lock()
        self._seen: set[str] = set()
        self.states: dict[str, bool] = {}
        self.last_ring: float = 0.0
        if bus is not None:
            bus.subscribe("frigate/events", self._on_frigate)
            if cfg.doorbell.ring_topic:
                bus.subscribe(cfg.doorbell.ring_topic, self._on_ring)
            for sw in cfg.switches:
                if sw.state_topic:
                    bus.subscribe(sw.state_topic, lambda t, p, sw=sw: self._on_switch_state(sw, p))

    # --- clientes SSE -------------------------------------------------
    def listen(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            self._clients.append(q)
        return q

    def unlisten(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)

    def emit(self, event: dict) -> None:
        event.setdefault("ts", self._clock())
        with self._lock:
            clients = list(self._clients)
        for q in clients:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass

    # --- entradas MQTT ------------------------------------------------
    def _on_frigate(self, topic: str, payload: bytes) -> None:
        try:
            ev = json.loads(payload)
            after = ev.get("after") or {}
            label, camera, oid = after.get("label"), after.get("camera"), after.get("id")
        except (ValueError, AttributeError):
            return
        known = {c.name for c in self.cfg.cameras}
        if not oid or label not in self.cfg.labels or (known and camera not in known):
            return
        if oid in self._seen:
            return
        self._seen.add(oid)
        if len(self._seen) > 500:
            self._seen = set(list(self._seen)[-200:])
        self.emit({"kind": "detect", "camera": camera, "label": label, "id": oid})
        if label in self.cfg.notify_labels and self._notify:
            where = camera
            if camera == self.cfg.doorbell.camera:
                where = f"{camera} (timbre)"
            self._notify(f"{label} en {where}", camera)

    def _on_ring(self, topic: str, payload: bytes) -> None:
        want = self.cfg.doorbell.ring_payload
        if want and payload.decode(errors="replace").strip() != want:
            return
        now = self._clock()
        if now - self.last_ring < 5:        # algunos timbres repiten el aviso
            return
        self.last_ring = now
        self.emit({"kind": "ring", "camera": self.cfg.doorbell.camera})
        if self._notify:
            self._notify("Tocaron el timbre", self.cfg.doorbell.camera)

    def _on_switch_state(self, sw, payload: bytes) -> None:
        text = payload.decode(errors="replace").strip()
        on = text == sw.on
        self.states[sw.name] = on
        self.emit({"kind": "switch", "name": sw.name, "on": on})

    # --- salidas ------------------------------------------------------
    def set_switch(self, name: str, on: bool) -> bool:
        sw = next((s for s in self.cfg.switches if s.name == name), None)
        if sw is None or self.bus is None:
            return False
        self.bus.publish(sw.command_topic, sw.on if on else sw.off)
        if not sw.state_topic:              # sin retorno de estado: se asume el pedido
            self.states[name] = on
            self.emit({"kind": "switch", "name": name, "on": on})
        return True

    def open_door(self) -> bool:
        d = self.cfg.doorbell
        if not d.open_topic or self.bus is None:
            return False
        self.bus.publish(d.open_topic, d.open_payload)
        return True
