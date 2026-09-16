from fuera_gatos.deterrents.servo import LogServoDriver
from fuera_gatos.deterrents.turret import AxisMap, WaterTurret


class FakeValve:
    def __init__(self):
        self.state = []

    def on(self):
        self.state.append("on")

    def off(self):
        self.state.append("off")


def make_turret(**kw):
    servo = LogServoDriver()
    valve = FakeValve()
    t = WaterTurret(
        "torreta", servo, pan_channel=0, tilt_channel=1,
        pan_map=AxisMap([[0, 150], [640, 30]], limits=(40, 140)),
        tilt_map=AxisMap([[100, 80], [480, 20]]),
        valve=valve, max_on_s=5.0, **kw,
    )
    return t, servo, valve


def test_axis_map_is_linear_and_clamped():
    m = AxisMap([[0, 150], [640, 30]], limits=(40, 140))
    assert m(320) == 90
    assert m(0) == 140    # 150 recortado al límite mecánico
    assert m(640) == 40   # 30 recortado
    assert m(-1000) == 140


def test_aim_moves_servos_to_pixel_position():
    t, servo, _ = make_turret(lead_s=0.0)
    pan, tilt = t.aim(320, 290, ts=0.0)
    assert pan == 90 and tilt == 50
    assert servo.angles == {0: 90.0, 1: 50.0}


def test_aim_leads_moving_target():
    t, servo, _ = make_turret(lead_s=0.5)
    t.aim(100, 300, ts=0.0)
    t.aim(200, 300, ts=0.25)  # 400 px/s hacia la derecha
    assert t.aimed_at[0] == 400  # 200 + 400 * 0.5


def test_small_moves_are_ignored_to_avoid_jitter():
    t, servo, _ = make_turret(lead_s=0.0)
    t.aim(320, 290, ts=0.0)
    n = len(servo.history)
    t.aim(321, 291, ts=0.1)
    assert len(servo.history) == n


def test_valve_opens_and_closes_with_activation():
    import time

    t, servo, valve = make_turret(lead_s=0.0)
    t.aim(320, 290, ts=0.0)
    t.start(0.1)
    assert valve.state == ["on"]
    time.sleep(0.3)
    assert valve.state == ["on", "off"]
    assert not t.active


def test_controller_pre_aims_and_tracks_while_active(env):
    from fuera_gatos.detection.base import Detection
    from fuera_gatos.config import EscalationLevel

    ctrl, dets, events, clock = env(escalation=[EscalationLevel("agua", ["torreta"], 4.0)])
    t, servo, valve = make_turret(lead_s=0.0)
    ctrl.deterrents["torreta"] = t
    cat = Detection("cat", 0.9, (300, 250, 340, 290), zone="jardin")
    ctrl.process([cat])            # confirmando: ya apunta
    assert servo.angles[0] == 90
    clock.advance(0.25)
    ctrl.process([cat])
    clock.advance(0.25)
    ctrl.process([cat])            # activa
    assert valve.state == ["on"]
    clock.advance(0.25)
    moved = Detection("cat", 0.9, (100, 250, 140, 290), zone="jardin")
    ctrl.process([moved])          # sigue al gato mientras está activa
    assert servo.angles[0] == AxisMap([[0, 150], [640, 30]], limits=(40, 140))(120)
