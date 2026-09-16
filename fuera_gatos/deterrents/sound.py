"""Disuasor sonoro: reproduce un WAV (bufido, chorro de aire, etc.) con un reproductor externo."""
from __future__ import annotations

import logging
import random
import shutil
import subprocess
from pathlib import Path

from .base import TimedDeterrent

log = logging.getLogger(__name__)

_PLAYERS = {
    "aplay": ["aplay", "-q"],
    "paplay": ["paplay"],
    "ffplay": ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
}


class SoundDeterrent(TimedDeterrent):
    def __init__(self, name: str, files: list[str], player: str = "aplay", max_on_s: float = 10.0):
        super().__init__(name, max_on_s)
        self.files = [Path(f) for f in files]
        missing = [str(f) for f in self.files if not f.exists()]
        if missing:
            log.warning(
                "Archivos de sonido inexistentes (ejecuta scripts/make_sounds.py): %s", missing
            )
        self.files = [f for f in self.files if f.exists()]
        if player not in _PLAYERS:
            raise ValueError(f"Reproductor desconocido: {player}")
        self._cmd = _PLAYERS[player]
        if shutil.which(self._cmd[0]) is None:
            log.warning("No se encontró el reproductor '%s'; el sonido no funcionará", player)
        self._proc: subprocess.Popen | None = None

    def _on(self) -> None:
        if not self.files:
            log.warning("Sin archivos de sonido; '%s' no hace nada", self.name)
            return
        f = random.choice(self.files)
        self._proc = subprocess.Popen(self._cmd + [str(f)], stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL)
        log.info("Sonido '%s': %s", self.name, f.name)

    def _off(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None
