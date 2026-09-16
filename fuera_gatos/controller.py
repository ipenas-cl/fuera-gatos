"""Lógica de decisión: cuándo y cómo asustar al gato.

Es código puro (sin cámara ni GPIO) para poder probarlo con reloj simulado.

Estados:
    IDLE        -> sin gato.
    CONFIRMING  -> se vio un gato, esperando N detecciones en la ventana.
    ACTIVE      -> disuasores encendidos por `duration_s`.
    COOLDOWN    -> pausa obligatoria antes de volver a actuar.

Medidas para no dañar ni abusar:
    * Confirmación por varias detecciones (evita falsos positivos).
    * Duración corta por nivel y tope duro en cada disuasor.
    * Cooldown entre activaciones y máximo por hora.
    * Si aparece una persona o un perro en el cuadro, se apaga todo.
    * Horario silencioso: de noche solo disuasores no audibles.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable

from .config import ControllerConfig, EscalationLevel, QuietHours
from .detection.base import Detection
from .deterrents.base import Deterrent

log = logging.getLogger(__name__)


class State(str, Enum):
    IDLE = "idle"
    CONFIRMING = "confirming"
    ACTIVE = "active"
    COOLDOWN = "cooldown"


@dataclass
class Event:
    kind: str  # activated | suppressed | rate_limited | ended | detected
    ts: float
    level: str | None = None
    deterrents: list[str] = field(default_factory=list)
    detections: list[Detection] = field(default_factory=list)
    reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "ts": self.ts,
            "level": self.level,
            "deterrents": list(self.deterrents),
            "detections": [
                {"label": d.label, "confidence": d.confidence, "bbox": list(d.bbox), "zone": d.zone}
                for d in self.detections
            ],
            "reason": self.reason,
        }


def _parse_hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def in_quiet_hours(quiet: QuietHours | None, now: datetime) -> bool:
    if quiet is None:
        return False
    start, end = _parse_hhmm(quiet.start), _parse_hhmm(quiet.end)
    cur = now.hour * 60 + now.minute
    if start == end:
        return False
    if start < end:
        return start <= cur < end
    return cur >= start or cur < end  # cruza medianoche


class Controller:
    def __init__(
        self,
        cfg: ControllerConfig,
        deterrents: dict[str, Deterrent],
        target_labels: list[str],
        suppress_labels: list[str] | None = None,
        clock: Callable[[], float] = time.monotonic,
        wallclock: Callable[[], datetime] = datetime.now,
        on_event: Callable[[Event], None] | None = None,
        zone_deterrents: dict[str, list[str] | None] | None = None,
    ):
        if not cfg.escalation:
            raise ValueError("Se necesita al menos un nivel de escalado")
        self.cfg = cfg
        self.deterrents = deterrents
        self.targets = set(target_labels)
        self.suppress = set(suppress_labels or [])
        self.clock = clock
        self.wallclock = wallclock
        self.on_event = on_event or (lambda e: None)
        # zona -> disuasores permitidos (None = todos)
        self.zone_deterrents = zone_deterrents or {}

        self.state = State.IDLE
        self._confirm_hits: deque[float] = deque()
        self._active_until = 0.0
        self._active_names: list[str] = []
        self._cooldown_until = 0.0
        self._activations: deque[float] = deque()  # marcas de tiempo de la última hora
        self._last_activation_ts: float | None = None
        self._last_level_idx = -1
        self._suppressed = False

    # ------------------------------------------------------------------ API
    def process(self, detections: list[Detection]) -> State:
        """Procesa las detecciones de un cuadro y devuelve el estado resultante."""
        now = self.clock()
        self._advance_timers(now)

        if any(d.label in self.suppress for d in detections):
            self._suppress(now, detections)
            return self.state
        self._suppressed = False

        targets = [d for d in detections if d.label in self.targets]

        if self.state == State.ACTIVE:
            self._aim(targets, now, self._active_names)
            return self.state
        if self.state == State.COOLDOWN:
            return self.state

        if not targets:
            self._confirm_hits.clear()
            self.state = State.IDLE
            return self.state

        # Pre-apuntar mientras se confirma, para que el chorro salga ya dirigido.
        self._aim(targets, now, list(self.deterrents))

        self._confirm_hits.append(now)
        window_start = now - self.cfg.confirm_window_s
        while self._confirm_hits and self._confirm_hits[0] < window_start:
            self._confirm_hits.popleft()

        if len(self._confirm_hits) >= self.cfg.confirm_frames:
            self._activate(now, targets)
        else:
            self.state = State.CONFIRMING
        return self.state

    def tick(self) -> State:
        """Llamar periódicamente aunque no haya cuadros (apaga por tiempo)."""
        self._advance_timers(self.clock())
        return self.state

    def stop_all(self) -> None:
        for d in self.deterrents.values():
            try:
                d.stop()
            except Exception:
                log.exception("Error apagando '%s'", d.name)
        self._active_names = []

    def close(self) -> None:
        self.stop_all()
        for d in self.deterrents.values():
            try:
                d.close()
            except Exception:
                log.exception("Error cerrando '%s'", d.name)

    # -------------------------------------------------------------- interno
    def _advance_timers(self, now: float) -> None:
        if self.state == State.ACTIVE and now >= self._active_until:
            self.stop_all()
            self.state = State.COOLDOWN
            # El cooldown cuenta desde el fin real de la activación, no desde
            # el momento en que se detectó (por si hubo cuadros perdidos).
            self._cooldown_until = self._active_until + self.cfg.cooldown_s
            self.on_event(Event("ended", self._active_until))
        if self.state == State.COOLDOWN and now >= self._cooldown_until:
            self.state = State.IDLE
            self._confirm_hits.clear()

    def _suppress(self, now: float, detections: list[Detection]) -> None:
        was_active = self.state == State.ACTIVE
        if was_active:
            self.stop_all()
            self.state = State.COOLDOWN
            self._cooldown_until = now + self.cfg.cooldown_s
        elif self.state != State.COOLDOWN:
            self.state = State.IDLE
        self._confirm_hits.clear()
        if self._suppressed and not was_active:
            return  # ya se avisó; no repetir el evento en cada cuadro
        self._suppressed = True
        labels = sorted({d.label for d in detections if d.label in self.suppress})
        self.on_event(
            Event("suppressed", now, detections=detections,
                  reason=f"presencia de {', '.join(labels)}" + (" (apagado inmediato)" if was_active else ""))
        )

    def _aim(self, targets: list[Detection], now: float, names: list[str]) -> None:
        """Orienta los disuasores que saben apuntar hacia el gato más grande (el más cercano)."""
        if not targets:
            return
        target = max(targets, key=lambda d: d.area)
        x, y = target.anchor
        for n in names:
            det = self.deterrents.get(n)
            aim = getattr(det, "aim", None)
            if aim is None:
                continue
            try:
                aim(x, y, now)
            except Exception:
                log.exception("No se pudo apuntar '%s'", n)

    def _pick_level(self, now: float) -> tuple[int, EscalationLevel]:
        idx = 0
        if (
            self._last_activation_ts is not None
            and now - self._last_activation_ts <= self.cfg.escalate_if_return_within_s
        ):
            idx = min(self._last_level_idx + 1, len(self.cfg.escalation) - 1)
        return idx, self.cfg.escalation[idx]

    def _allowed_now(self, names: list[str], targets: list[Detection]) -> list[str]:
        names = list(names)
        if in_quiet_hours(self.cfg.quiet_hours, self.wallclock()):
            allowed = set(self.cfg.quiet_hours.allowed)  # type: ignore[union-attr]
            names = [n for n in names if n in allowed]
        # Un disuasor solo se usa si TODAS las zonas donde hay gato lo permiten:
        # si hay un gato en el techo y otro en el jardín, el agua no se activa.
        zones = {d.zone for d in targets if d.zone}
        for z in zones:
            allowed_in_zone = self.zone_deterrents.get(z)
            if allowed_in_zone is not None:
                names = [n for n in names if n in allowed_in_zone]
        return names

    def _activate(self, now: float, targets: list[Detection]) -> None:
        self._confirm_hits.clear()
        while self._activations and self._activations[0] < now - 3600:
            self._activations.popleft()
        if len(self._activations) >= self.cfg.max_activations_per_hour:
            self.state = State.COOLDOWN
            self._cooldown_until = now + self.cfg.cooldown_s
            self.on_event(Event("rate_limited", now, detections=targets,
                                reason="máximo de activaciones por hora alcanzado"))
            return

        idx, level = self._pick_level(now)
        names = self._allowed_now(level.deterrents, targets)
        if not names:
            self.state = State.COOLDOWN
            self._cooldown_until = now + self.cfg.cooldown_s
            self.on_event(Event("rate_limited", now, level=level.name, detections=targets,
                                reason="ningún disuasor permitido (horario silencioso o zona)"))
            return

        started = []
        for n in names:
            det = self.deterrents.get(n)
            if det is None:
                log.warning("Disuasor '%s' no disponible", n)
                continue
            try:
                det.start(level.duration_s)
                started.append(n)
            except Exception:
                log.exception("No se pudo activar '%s'", n)

        self.state = State.ACTIVE
        self._active_until = now + level.duration_s
        self._active_names = started
        self._activations.append(now)
        self._last_activation_ts = now
        self._last_level_idx = idx
        self.on_event(Event("activated", now, level=level.name, deterrents=started, detections=targets))
