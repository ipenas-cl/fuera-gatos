from datetime import datetime

import pytest

from fuera_gatos.config import ControllerConfig, EscalationLevel, QuietHours
from fuera_gatos.controller import Controller
from fuera_gatos.detection.base import Detection
from fuera_gatos.deterrents.simulated import LogDeterrent


class FakeClock:
    def __init__(self, start: float = 0.0, hour: int = 12):
        self.t = start
        self.hour = hour

    def __call__(self) -> float:
        return self.t

    def wall(self) -> datetime:
        from datetime import timedelta

        return datetime(2026, 1, 1, self.hour, 0, 0) + timedelta(seconds=self.t)

    def advance(self, s: float) -> None:
        self.t += s


def make_cfg(**overrides) -> ControllerConfig:
    base = dict(
        confirm_frames=3,
        confirm_window_s=2.0,
        cooldown_s=30.0,
        max_activations_per_hour=5,
        escalate_if_return_within_s=300.0,
        escalation=[
            EscalationLevel("nivel_1", ["luz", "sonido"], 4.0),
            EscalationLevel("nivel_2", ["luz", "aspersor"], 3.0),
        ],
        quiet_hours=QuietHours("22:00", "07:00", ["luz", "aspersor"]),
    )
    base.update(overrides)
    return ControllerConfig(**base)


@pytest.fixture
def cat():
    return Detection("cat", 0.9, (100, 300, 180, 380), zone="basura")


@pytest.fixture
def person():
    return Detection("person", 0.9, (300, 100, 400, 460))


@pytest.fixture
def env():
    def _make(hour: int = 12, zone_deterrents=None, **overrides):
        clock = FakeClock(hour=hour)
        dets = {n: LogDeterrent(n, use_timer=False, max_on_s=5.0) for n in ("luz", "sonido", "aspersor")}
        events = []
        ctrl = Controller(
            make_cfg(**overrides), dets, ["cat"], ["person", "dog"],
            clock=clock, wallclock=clock.wall, on_event=events.append,
            zone_deterrents=zone_deterrents,
        )
        return ctrl, dets, events, clock

    return _make
