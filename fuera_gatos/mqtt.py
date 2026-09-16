"""Cliente MQTT compartido (paho-mqtt) con reconexión y suscripciones por prefijo."""
from __future__ import annotations

import json
import logging
import threading
from typing import Callable

log = logging.getLogger(__name__)


class MqttBus:
    """Envoltura mínima: publish(topic, payload) y subscribe(topic, callback(topic, payload))."""

    def __init__(self, host: str = "localhost", port: int = 1883, username: str | None = None,
                 password: str | None = None, client_id: str = "fuera-gatos"):
        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Falta 'paho-mqtt'. Instalar con: pip install 'fuera-gatos[mqtt]'") from exc
        self._handlers: dict[str, list[Callable[[str, bytes], None]]] = {}
        self._lock = threading.Lock()
        self.connected = threading.Event()
        try:
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        except (AttributeError, TypeError):  # paho < 2
            self._client = mqtt.Client(client_id=client_id)
        if username:
            self._client.username_pw_set(username, password)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(1, 30)
        self._client.connect_async(host, port, keepalive=30)
        self._client.loop_start()

    # paho 1.x y 2.x pasan distinta cantidad de argumentos; se aceptan todos.
    def _on_connect(self, client, userdata, flags, rc, *args):
        code = getattr(rc, "value", rc)
        if code == 0:
            log.info("MQTT conectado")
            self.connected.set()
            with self._lock:
                for topic in self._handlers:
                    client.subscribe(topic)
        else:
            log.warning("MQTT: conexión rechazada (%s)", rc)

    def _on_message(self, client, userdata, msg):
        with self._lock:
            handlers = [h for pat, hs in self._handlers.items() if _match(pat, msg.topic) for h in hs]
        for h in handlers:
            try:
                h(msg.topic, msg.payload)
            except Exception:
                log.exception("Error procesando %s", msg.topic)

    def subscribe(self, topic: str, handler: Callable[[str, bytes], None]) -> None:
        with self._lock:
            new = topic not in self._handlers
            self._handlers.setdefault(topic, []).append(handler)
        if new and self.connected.is_set():
            self._client.subscribe(topic)

    def publish(self, topic: str, payload, retain: bool = False) -> None:
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        self._client.publish(topic, payload, qos=1, retain=retain)

    def close(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:  # pragma: no cover
            pass


def _match(pattern: str, topic: str) -> bool:
    """Coincidencia MQTT con comodines + y #."""
    p, t = pattern.split("/"), topic.split("/")
    for i, part in enumerate(p):
        if part == "#":
            return True
        if i >= len(t):
            return False
        if part != "+" and part != t[i]:
            return False
    return len(p) == len(t)


class FakeBus:
    """Bus en memoria para pruebas y simulación."""

    def __init__(self) -> None:
        self.published: list[tuple[str, str, bool]] = []
        self._handlers: dict[str, list[Callable[[str, bytes], None]]] = {}
        self.connected = threading.Event()
        self.connected.set()

    def subscribe(self, topic: str, handler) -> None:
        self._handlers.setdefault(topic, []).append(handler)

    def publish(self, topic: str, payload, retain: bool = False) -> None:
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        self.published.append((topic, str(payload), retain))

    def inject(self, topic: str, payload) -> None:
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        data = payload.encode() if isinstance(payload, str) else payload
        for pat, hs in self._handlers.items():
            if _match(pat, topic):
                for h in hs:
                    h(topic, data)

    def close(self) -> None:
        pass
