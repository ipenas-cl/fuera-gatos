from fuera_gatos.controller import State


def frames(ctrl, clock, dets, n, dt=0.25):
    for _ in range(n):
        ctrl.process(list(dets))
        clock.advance(dt)


def test_needs_confirmation_before_acting(env, cat):
    ctrl, dets, events, clock = env()
    assert ctrl.process([cat]) == State.CONFIRMING
    clock.advance(0.25)
    assert ctrl.process([cat]) == State.CONFIRMING
    assert not dets["luz"].active
    clock.advance(0.25)
    assert ctrl.process([cat]) == State.ACTIVE
    assert dets["luz"].active and dets["sonido"].active
    assert not dets["aspersor"].active
    assert events[-1].kind == "activated" and events[-1].level == "nivel_1"


def test_single_glimpse_does_not_trigger(env, cat):
    ctrl, dets, events, clock = env()
    ctrl.process([cat])
    clock.advance(3.0)  # fuera de la ventana de confirmación
    ctrl.process([cat])
    clock.advance(0.1)
    assert ctrl.process([cat]) == State.CONFIRMING
    assert not events


def test_deterrents_stop_after_duration_and_cooldown_applies(env, cat):
    ctrl, dets, events, clock = env()
    frames(ctrl, clock, [cat], 3)
    assert ctrl.state == State.ACTIVE
    clock.advance(4.0)
    assert ctrl.process([cat]) == State.COOLDOWN
    assert not dets["luz"].active and not dets["sonido"].active
    assert events[-1].kind == "ended"
    # Durante el cooldown el gato sigue ahí pero no se reactiva
    frames(ctrl, clock, [cat], 5)
    assert ctrl.state == State.COOLDOWN
    clock.advance(30.0)
    assert ctrl.process([]) == State.IDLE


def test_escalates_when_cat_returns_soon(env, cat):
    ctrl, dets, events, clock = env()
    frames(ctrl, clock, [cat], 3)
    clock.advance(40.0)
    ctrl.process([])
    frames(ctrl, clock, [cat], 3)
    acts = [e for e in events if e.kind == "activated"]
    assert [a.level for a in acts] == ["nivel_1", "nivel_2"]
    assert dets["aspersor"].active
    # Se queda en el nivel máximo, no se pasa de la lista
    clock.advance(40.0)
    ctrl.process([])
    frames(ctrl, clock, [cat], 3)
    assert [e.level for e in events if e.kind == "activated"][-1] == "nivel_2"


def test_resets_to_first_level_after_long_absence(env, cat):
    ctrl, dets, events, clock = env()
    frames(ctrl, clock, [cat], 3)
    clock.advance(600.0)
    ctrl.process([])
    frames(ctrl, clock, [cat], 3)
    assert [e.level for e in events if e.kind == "activated"] == ["nivel_1", "nivel_1"]


def test_person_in_frame_suppresses_and_shuts_off(env, cat, person):
    ctrl, dets, events, clock = env()
    frames(ctrl, clock, [cat], 3)
    assert dets["luz"].active
    ctrl.process([cat, person])
    assert not dets["luz"].active and not dets["sonido"].active
    assert ctrl.state == State.COOLDOWN
    assert events[-1].kind == "suppressed" and "person" in events[-1].reason


def test_person_alone_prevents_confirmation(env, cat, person):
    ctrl, dets, events, clock = env()
    frames(ctrl, clock, [cat, person], 6)
    assert not any(e.kind == "activated" for e in events)
    assert not dets["luz"].active
    # Un solo aviso mientras la persona sigue ahí; otro cuando vuelve a aparecer
    assert [e.kind for e in events] == ["suppressed"]
    frames(ctrl, clock, [], 2)
    frames(ctrl, clock, [person], 2)
    assert [e.kind for e in events] == ["suppressed", "suppressed"]


def test_rate_limit_per_hour(env, cat):
    ctrl, dets, events, clock = env(max_activations_per_hour=2)
    for _ in range(3):
        frames(ctrl, clock, [cat], 3)
        clock.advance(40.0)
        ctrl.process([])
    kinds = [e.kind for e in events if e.kind in ("activated", "rate_limited")]
    assert kinds == ["activated", "activated", "rate_limited"]
    # Una hora después vuelve a permitir
    clock.advance(3600.0)
    ctrl.process([])
    frames(ctrl, clock, [cat], 3)
    assert events[-1].kind == "activated"


def test_quiet_hours_only_allow_silent_deterrents(env, cat):
    ctrl, dets, events, clock = env(hour=23)
    frames(ctrl, clock, [cat], 3)
    assert events[-1].kind == "activated"
    assert events[-1].deterrents == ["luz"]
    assert dets["luz"].active and not dets["sonido"].active


def test_quiet_hours_with_nothing_allowed_does_not_act(env, cat):
    from fuera_gatos.config import QuietHours

    ctrl, dets, events, clock = env(hour=2, quiet_hours=QuietHours("22:00", "07:00", []))
    frames(ctrl, clock, [cat], 3)
    assert events[-1].kind == "rate_limited"
    assert not any(d.active for d in dets.values())


def test_duration_capped_by_deterrent_hard_limit(env, cat):
    from fuera_gatos.config import EscalationLevel

    ctrl, dets, events, clock = env(escalation=[EscalationLevel("largo", ["aspersor"], 30.0)])
    frames(ctrl, clock, [cat], 3)
    assert dets["aspersor"].calls[-1] == ("start", 5.0)


def test_close_stops_everything(env, cat):
    ctrl, dets, events, clock = env()
    frames(ctrl, clock, [cat], 3)
    ctrl.close()
    assert not any(d.active for d in dets.values())


def test_in_quiet_hours_helper():
    from datetime import datetime

    from fuera_gatos.config import QuietHours
    from fuera_gatos.controller import in_quiet_hours

    q = QuietHours("22:00", "07:00", [])
    assert in_quiet_hours(q, datetime(2026, 1, 1, 23, 30))
    assert in_quiet_hours(q, datetime(2026, 1, 1, 3, 0))
    assert not in_quiet_hours(q, datetime(2026, 1, 1, 7, 0))
    assert not in_quiet_hours(q, datetime(2026, 1, 1, 12, 0))
    assert not in_quiet_hours(None, datetime(2026, 1, 1, 23, 0))
    day = QuietHours("13:00", "15:00", [])
    assert in_quiet_hours(day, datetime(2026, 1, 1, 14, 0))
    assert not in_quiet_hours(day, datetime(2026, 1, 1, 16, 0))


def test_zone_can_forbid_deterrents(env, cat):
    from fuera_gatos.detection.base import Detection

    ctrl, dets, events, clock = env(zone_deterrents={"techo": ["luz"], "jardin": None})
    roof_cat = Detection("cat", 0.9, (200, 50, 260, 90), zone="techo")
    frames(ctrl, clock, [roof_cat], 3)
    assert events[-1].kind == "activated" and events[-1].deterrents == ["luz"]
    assert not dets["sonido"].active
    # Vuelve pronto (nivel 2 con aspersor) pero en el techo: agua no, luz sí
    clock.advance(40.0)
    ctrl.process([])
    frames(ctrl, clock, [roof_cat], 3)
    assert events[-1].level == "nivel_2" and events[-1].deterrents == ["luz"]
    assert not dets["aspersor"].active


def test_cat_in_roof_and_garden_blocks_water_for_both(env, cat):
    from fuera_gatos.detection.base import Detection

    ctrl, dets, events, clock = env(zone_deterrents={"techo": ["luz"], "basura": None})
    roof_cat = Detection("cat", 0.9, (200, 50, 260, 90), zone="techo")
    frames(ctrl, clock, [cat, roof_cat], 3)
    assert events[-1].deterrents == ["luz"]
