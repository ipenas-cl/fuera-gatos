import time

from fuera_gatos.deterrents.simulated import LogDeterrent


def test_timer_stops_deterrent_by_itself():
    d = LogDeterrent("aspersor", max_on_s=5.0)
    d.start(0.15)
    assert d.active
    time.sleep(0.35)
    assert not d.active
    assert [c[0] for c in d.calls] == ["start", "on", "stop", "off"]


def test_hard_limit_caps_duration():
    d = LogDeterrent("aspersor", max_on_s=0.1)
    d.start(10.0)
    time.sleep(0.3)
    assert not d.active


def test_pulsed_output_toggles_and_ends_off():
    d = LogDeterrent("aspersor", max_on_s=5.0, pulse_on_s=0.05, pulse_off_s=0.05)
    d.start(0.32)
    time.sleep(0.6)
    kinds = [c[0] for c in d.calls if c[0] in ("on", "off")]
    assert kinds.count("on") >= 3
    assert kinds[-1] == "off"
    assert not d.active


def test_stop_cancels_pulses():
    d = LogDeterrent("aspersor", max_on_s=5.0, pulse_on_s=0.05, pulse_off_s=0.05)
    d.start(2.0)
    time.sleep(0.12)
    d.stop()
    n = len(d.calls)
    time.sleep(0.2)
    assert len(d.calls) == n
    assert not d.active
