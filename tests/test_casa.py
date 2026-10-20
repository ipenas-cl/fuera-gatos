import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from fuera_gatos.casa.config import casa_from_dict
from fuera_gatos.casa.hub import Hub
from fuera_gatos.casa.server import CasaServer, frigate_path_allowed
from fuera_gatos.config import ConfigError
from fuera_gatos.mqtt import FakeBus

RAW = {
    "server": {"token": "secreta"},
    "mqtt": {"host": "x"},
    "cameras": [{"name": "timbre"}, {"name": "frente"}],
    "doorbell": {"camera": "timbre", "ring_topic": "casa/timbre/ring", "open_topic": "casa/puerta"},
    "switches": [{"name": "luz", "command_topic": "luz/set", "state_topic": "luz/state"}],
}


class FakeFrigate(BaseHTTPRequestHandler):
    def log_message(self, *a): ...

    def do_GET(self):
        if self.path.startswith("/api/events?"):
            body = json.dumps([{"id": "e1", "camera": "timbre", "label": "person", "start_time": 1.0,
                                "end_time": 2.0, "has_clip": True, "data": {"top_score": 0.87}}]).encode()
            ctype = "application/json"
        else:
            body, ctype = b"\xff\xd8jpg", "image/jpeg"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def app():
    fr = HTTPServer(("127.0.0.1", 0), FakeFrigate)
    threading.Thread(target=fr.serve_forever, daemon=True).start()
    raw = dict(RAW, frigate={"url": f"http://127.0.0.1:{fr.server_port}"})
    cfg = casa_from_dict(raw)
    bus = FakeBus()
    hub = Hub(cfg, bus, clock=iter(range(100, 10_000, 10)).__next__)
    srv = CasaServer(cfg, hub)
    httpd = srv.make_httpd("127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}", bus, hub
    httpd.shutdown()
    fr.shutdown()


def call(url, data=None, token="secreta"):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(req, timeout=5)


def test_config_validation():
    with pytest.raises(ConfigError):
        casa_from_dict({"cameras": [{"name": "a"}], "doorbell": {"camera": "b"}})
    with pytest.raises(ConfigError):
        casa_from_dict({"switches": [{"name": "luz", "command_topic": "x"}]})   # falta mqtt.host


def test_frigate_whitelist():
    cams = {"timbre"}
    assert frigate_path_allowed("api/timbre/latest.jpg", cams)
    assert frigate_path_allowed("api/events/123.4-abc/clip.mp4", cams)
    assert not frigate_path_allowed("api/frente/latest.jpg", cams)
    assert not frigate_path_allowed("api/config", cams)
    assert not frigate_path_allowed("api/events/123/delete", cams)
    assert not frigate_path_allowed("api/../config", cams)


def test_requires_token(app):
    base, _, _ = app
    with pytest.raises(urllib.error.HTTPError) as e:
        call(base + "/api/config", token="")
    assert e.value.code == 401
    with pytest.raises(urllib.error.HTTPError) as e:
        call(base + "/api/config", token="mala")
    assert e.value.code == 401
    assert json.load(call(base + "/api/config"))["cameras"][0]["name"] == "timbre"


def test_events_and_snapshot_proxy(app):
    base, _, _ = app
    evs = json.load(call(base + "/api/events"))
    assert evs[0]["id"] == "e1" and evs[0]["score"] == 0.87 and evs[0]["has_clip"]
    assert call(base + "/frigate/api/timbre/latest.jpg").read().startswith(b"\xff\xd8")
    with pytest.raises(urllib.error.HTTPError) as e:
        call(base + "/frigate/api/config")
    assert e.value.code == 403


def test_switch_and_door(app):
    base, bus, hub = app
    call(base + "/api/switch/luz", {"on": True})
    assert ("luz/set", "ON", False) in bus.published
    bus.inject("luz/state", "OFF")
    assert hub.states["luz"] is False
    with pytest.raises(urllib.error.HTTPError) as e:
        call(base + "/api/switch/nada", {"on": True})
    assert e.value.code == 404
    call(base + "/api/door/open", {})
    assert ("casa/puerta", "ON", False) in bus.published


def test_ring_and_detect_events():
    cfg = casa_from_dict(RAW)
    bus, sent = FakeBus(), []
    now = [100.0]
    hub = Hub(cfg, bus, notify=lambda text, cam: sent.append((text, cam)), clock=lambda: now[0])
    q = hub.listen()
    bus.inject("casa/timbre/ring", "1")
    now[0] += 2
    bus.inject("casa/timbre/ring", "1")        # rebote a los 2 s: se ignora
    assert q.get_nowait()["kind"] == "ring" and q.empty()
    bus.inject("frigate/events", {"type": "new", "after": {"id": "a", "camera": "timbre", "label": "person"}})
    bus.inject("frigate/events", {"type": "update", "after": {"id": "a", "camera": "timbre", "label": "person"}})
    bus.inject("frigate/events", {"type": "new", "after": {"id": "b", "camera": "frente", "label": "cat"}})
    bus.inject("frigate/events", {"type": "new", "after": {"id": "c", "camera": "otra", "label": "person"}})
    kinds = [(e["kind"], e.get("label")) for e in iter(lambda: q.get_nowait() if not q.empty() else None, None)]
    assert kinds == [("detect", "person"), ("detect", "cat")]
    assert [s[0] for s in sent] == ["Tocaron el timbre", "person en timbre (timbre)"]
