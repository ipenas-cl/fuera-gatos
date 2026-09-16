"""Simulación con reloj acelerado: muestra qué haría el sistema ante un guion de visitas."""
from __future__ import annotations

from datetime import datetime

from .config import AppConfig
from .controller import Controller, Event
from .detection.base import Detection
from .deterrents.simulated import LogDeterrent


def default_scenario(fps: float = 4.0):
    """Guion: gato en la basura, se va, vuelve a los 2 min, pasa una persona, gato de noche."""
    cat = Detection("cat", 0.8, (100, 300, 180, 380))
    person = Detection("person", 0.9, (300, 100, 400, 460))
    steps = []

    def add(seconds: float, dets: list[Detection], note: str = ""):
        n = max(1, int(seconds * fps))
        for i in range(n):
            steps.append((dets, note if i == 0 else ""))

    add(3, [], "inicio, sin gato")
    add(6, [cat], "gato aparece junto a la basura")
    add(5, [], "gato se va")
    add(120, [], "pasan 2 minutos")
    add(6, [cat], "el gato vuelve")
    add(40, [], "se va otra vez")
    add(5, [cat, person], "gato + persona en el cuadro (no se actúa)")
    add(5, [], "")
    return steps


def run_simulation(cfg: AppConfig, fps: float = 4.0, start_hour: int = 15) -> list[Event]:
    fake = {"t": 0.0}
    base_wall = datetime(2026, 1, 1, start_hour, 0, 0)

    def clock() -> float:
        return fake["t"]

    def wallclock() -> datetime:
        from datetime import timedelta

        return base_wall + timedelta(seconds=fake["t"])

    deterrents = {name: LogDeterrent(name, use_timer=False) for name in cfg.deterrents}
    events: list[Event] = []

    def on_event(ev: Event) -> None:
        events.append(ev)
        wall = wallclock().strftime("%H:%M:%S")
        if ev.kind == "activated":
            print(f"[{wall}] ACTIVADO {ev.level}: {', '.join(ev.deterrents)}")
        elif ev.kind == "ended":
            print(f"[{wall}] fin de activación, entra en cooldown")
        else:
            print(f"[{wall}] {ev.kind}: {ev.reason}")

    ctrl = Controller(
        cfg.controller,
        deterrents,
        target_labels=cfg.detector.target_labels,
        suppress_labels=cfg.detector.suppress_labels,
        clock=clock,
        wallclock=wallclock,
        on_event=on_event,
        zone_deterrents={z.name: z.deterrents for z in cfg.zones},
    )
    for dets, note in default_scenario(fps):
        if note:
            print(f"[{wallclock().strftime('%H:%M:%S')}] -- {note}")
        for d in dets:
            d.zone = d.zone or "basura"
        ctrl.process(list(dets))
        fake["t"] += 1.0 / fps
    ctrl.close()
    return events
