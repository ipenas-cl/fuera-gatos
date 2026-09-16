from fuera_gatos.config import EscalationLevel
from fuera_gatos.controller import State
from fuera_gatos.sensors import SimulatedSensor, guards_from_sensors


def frames(ctrl, clock, dets, n, dt=0.25):
    for _ in range(n):
        ctrl.process(list(dets))
        clock.advance(dt)


def test_empty_tank_blocks_water_but_not_light(env, cat):
    tank = SimulatedSensor("nivel", gates=["aspersor"], state=False)
    ctrl, dets, events, clock = env(
        escalation=[EscalationLevel("agua", ["aspersor", "luz"], 4.0)],
        guards=guards_from_sensors({"nivel": tank}),
    )
    frames(ctrl, clock, [cat], 3)
    kinds = [e.kind for e in events]
    assert kinds == ["resource_empty", "activated"]
    assert events[-1].deterrents == ["luz"]
    assert not dets["aspersor"].active and dets["luz"].active


def test_empty_notice_only_once_until_refilled(env, cat):
    tank = SimulatedSensor("nivel", gates=["aspersor"], state=False)
    ctrl, dets, events, clock = env(
        escalation=[EscalationLevel("agua", ["aspersor"], 4.0)],
        guards=guards_from_sensors({"nivel": tank}),
    )
    for _ in range(3):
        frames(ctrl, clock, [cat], 3)
        clock.advance(40.0)
        ctrl.process([])
    assert [e.kind for e in events].count("resource_empty") == 1
    assert not any(e.kind == "activated" for e in events)
    tank.state = True
    frames(ctrl, clock, [cat], 3)
    assert events[-1].kind == "activated" and events[-1].deterrents == ["aspersor"]
    tank.state = False
    clock.advance(40.0)
    ctrl.process([])
    frames(ctrl, clock, [cat], 3)
    assert [e.kind for e in events].count("resource_empty") == 2


def test_failing_sensor_counts_as_empty(env, cat):
    def boom():
        raise OSError("i2c")

    ctrl, dets, events, clock = env(
        escalation=[EscalationLevel("agua", ["aspersor"], 4.0)], guards={"aspersor": boom},
    )
    frames(ctrl, clock, [cat], 3)
    assert not dets["aspersor"].active
    assert ctrl.state == State.COOLDOWN


def test_roof_example_config_loads():
    from fuera_gatos.config import load_config

    cfg = load_config("examples/config.techo.yaml")
    assert cfg.sensors["nivel_estanque"].options["gates"] == ["torreta_a", "torreta_b"]
    own = next(z for z in cfg.zones if z.name == "techo_propio")
    assert own.deterrents is None
    for z in cfg.zones:
        if z.name.startswith("techo_vecino"):
            assert z.deterrents == []
