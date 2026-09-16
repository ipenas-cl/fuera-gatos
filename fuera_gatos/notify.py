"""Notificaciones opcionales (Telegram) sin dependencias externas."""
from __future__ import annotations

import json
import logging
import threading
import urllib.request
from pathlib import Path

from .config import NotifyConfig

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, cfg: NotifyConfig):
        self.cfg = cfg

    @property
    def enabled(self) -> bool:
        t = self.cfg.telegram
        return bool(t.enabled and t.token and t.chat_id)

    def send(self, text: str, photo: Path | None = None) -> None:
        if not self.enabled:
            return
        th = threading.Thread(target=self._send, args=(text, photo), daemon=True)
        th.start()

    def _send(self, text: str, photo: Path | None) -> None:
        t = self.cfg.telegram
        try:
            if photo and photo.exists() and photo.suffix.lower() in (".jpg", ".jpeg", ".png"):
                self._send_photo(t.token, t.chat_id, text, photo)
            else:
                url = f"https://api.telegram.org/bot{t.token}/sendMessage"
                body = json.dumps({"chat_id": t.chat_id, "text": text}).encode()
                req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=10).read()
        except Exception as exc:
            log.warning("No se pudo enviar la notificación: %s", exc)

    @staticmethod
    def _send_photo(token: str, chat_id: str, caption: str, photo: Path) -> None:
        boundary = "----fueragatos"
        parts = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n",
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n",
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{photo.name}\"\r\n"
            "Content-Type: image/jpeg\r\n\r\n",
        ]
        body = "".join(parts).encode() + photo.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        urllib.request.urlopen(req, timeout=20).read()
