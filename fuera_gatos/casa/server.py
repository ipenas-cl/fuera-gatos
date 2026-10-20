"""Servidor web del panel de casa. Solo biblioteca estándar: sirve la interfaz, hace de
proxy de Frigate (capturas, clips, historial) y empuja avisos en vivo por SSE."""
from __future__ import annotations

import hmac
import json
import logging
import queue
import re
import urllib.error
import urllib.request
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import CasaConfig
from .hub import Hub

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"

# Lo único de Frigate que se expone: imágenes, clips y miniaturas. Nada de su API de
# configuración ni de borrado.
_FRIGATE_OK = [
    re.compile(r"^api/(?P<cam>[\w.-]+)/latest\.jpg$"),
    re.compile(r"^api/events/[\w.-]+/(thumbnail\.jpg|snapshot\.jpg|clip\.mp4)$"),
    re.compile(r"^vod/event/[\w.-]+/index\.m3u8$"),
]


def frigate_path_allowed(path: str, cameras: set[str]) -> bool:
    for rx in _FRIGATE_OK:
        m = rx.match(path)
        if m:
            cam = m.groupdict().get("cam")
            return cam is None or not cameras or cam in cameras
    return False


def normalize_event(e: dict) -> dict:
    return {
        "id": e.get("id"),
        "camera": e.get("camera"),
        "label": e.get("label"),
        "score": round((e.get("data") or {}).get("top_score") or e.get("top_score") or 0, 2),
        "start": e.get("start_time"),
        "end": e.get("end_time"),
        "has_clip": bool(e.get("has_clip")),
    }


class CasaServer:
    def __init__(self, cfg: CasaConfig, hub: Hub, opener=urllib.request.urlopen):
        self.cfg, self.hub, self._open = cfg, hub, opener
        self.httpd: ThreadingHTTPServer | None = None

    def frigate_get(self, path: str, timeout: float = 10):
        return self._open(self.cfg.frigate_url + "/" + path, timeout=timeout)

    def make_httpd(self, host: str | None = None, port: int | None = None) -> ThreadingHTTPServer:
        app = self

        class Handler(_Handler):
            server_app = app

        self.httpd = ThreadingHTTPServer((host or self.cfg.server.host, self.cfg.server.port if port is None else port), Handler)
        self.httpd.daemon_threads = True
        return self.httpd


class _Handler(BaseHTTPRequestHandler):
    server_app: CasaServer
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # silencia el log por petición
        log.debug(fmt, *args)

    # --- utilidades ---------------------------------------------------
    def _send(self, code: int, body: bytes, ctype: str = "application/json", extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj).encode())

    def _authorized(self) -> bool:
        token = self.server_app.cfg.server.token
        if not token:
            return True
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        got = cookie["casa_token"].value if "casa_token" in cookie else ""
        got = got or self.headers.get("Authorization", "").removeprefix("Bearer ")
        return hmac.compare_digest(got.encode(), token.encode())

    # --- GET ----------------------------------------------------------
    def do_GET(self):
        app = self.server_app
        url = urlparse(self.path)
        path = url.path.lstrip("/")
        if path == "login.html" or path == "login":
            return self._send(200, (STATIC / "login.html").read_bytes(), "text/html; charset=utf-8")
        if not self._authorized():
            if path in ("", "index.html"):
                return self._send(302, b"", extra={"Location": "/login.html"})
            return self._json({"error": "no autorizado"}, 401)
        if path in ("", "index.html"):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path in ("manifest.json", "sw.js"):
            ctype = "application/json" if path.endswith("json") else "text/javascript"
            return self._send(200, (STATIC / path).read_bytes(), ctype)
        if path == "api/config":
            c = app.cfg
            return self._json({
                "cameras": [{"name": x.name, "title": x.title} for x in c.cameras],
                "doorbell": {"camera": c.doorbell.camera, "can_open": bool(c.doorbell.open_topic)},
                "switches": [{"name": s.name, "title": s.title, "on": app.hub.states.get(s.name)} for s in c.switches],
            })
        if path == "api/events":
            return self._events(parse_qs(url.query))
        if path == "api/stream":
            return self._stream()
        if path.startswith("frigate/"):
            return self._proxy(path[len("frigate/"):])
        self._json({"error": "no existe"}, 404)

    def _events(self, qs):
        app = self.server_app
        limit = min(int(qs.get("limit", ["40"])[0] or 40), 200)
        q = f"api/events?limit={limit}&has_snapshot=1"
        for key in ("camera", "label"):
            if qs.get(key):
                q += f"&{key}={qs[key][0]}"
        try:
            with app.frigate_get(q) as r:
                data = json.loads(r.read())
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return self._json({"error": f"Frigate no responde: {exc}"}, 502)
        self._json([normalize_event(e) for e in data])

    def _proxy(self, path: str):
        app = self.server_app
        if not frigate_path_allowed(path, {c.name for c in app.cfg.cameras}):
            return self._json({"error": "ruta no permitida"}, 403)
        try:
            with app.frigate_get(path, timeout=20) as r:
                body = r.read()
                ctype = r.headers.get("Content-Type", "application/octet-stream")
        except urllib.error.HTTPError as exc:
            return self._json({"error": "Frigate respondió %s" % exc.code}, 404 if exc.code == 404 else 502)
        except (urllib.error.URLError, OSError) as exc:
            return self._json({"error": f"Frigate no responde: {exc}"}, 502)
        self._send(200, body, ctype)

    def _stream(self):
        hub = self.server_app.hub
        q = hub.listen()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        try:
            while True:
                try:
                    ev = q.get(timeout=15)
                    chunk = f"data: {json.dumps(ev)}\n\n"
                except queue.Empty:
                    chunk = ": ping\n\n"
                self.wfile.write(chunk.encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            hub.unlisten(q)

    # --- POST ---------------------------------------------------------
    def do_POST(self):
        app = self.server_app
        path = urlparse(self.path).path.lstrip("/")
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._json({"error": "JSON inválido"}, 400)
        if path == "api/login":
            token = app.cfg.server.token
            ok = not token or hmac.compare_digest(str(body.get("token", "")).encode(), token.encode())
            if not ok:
                return self._json({"error": "clave incorrecta"}, 401)
            return self._send(200, b'{"ok":true}', extra={
                "Set-Cookie": f"casa_token={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000"})
        if not self._authorized():
            return self._json({"error": "no autorizado"}, 401)
        m = re.match(r"^api/switch/([\w.-]+)$", path)
        if m:
            if not app.hub.set_switch(m.group(1), bool(body.get("on"))):
                return self._json({"error": "interruptor desconocido"}, 404)
            return self._json({"ok": True})
        if path == "api/door/open":
            if not app.hub.open_door():
                return self._json({"error": "apertura no configurada"}, 404)
            return self._json({"ok": True})
        self._json({"error": "no existe"}, 404)
