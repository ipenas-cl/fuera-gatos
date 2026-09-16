import json

from fuera_gatos.detection.frigate import FrigateDetector
from fuera_gatos.deterrents.mqtt import MqttSwitch, build_mqtt_turret
from fuera_gatos.mqtt import FakeBus, _match
from fuera_gatos.sensors import MqttBinarySensor


def ev(kind, oid, camera="frente", label="cat", box=(100, 200, 180, 300), score=0.8, **extra):
    after = {"id": oid, "camera": camera, "label": label, "box": list(box), "score": score}
    after.update(extra)
    return {"type": kind, "after": after}


def test_topic_matching():
    assert _match("frigate/events", "frigate/events")
    assert _match("nodo/+/state", "nodo/agua/state")
    assert _match("frigate/#", "frigate/events/x")
    assert not _match("frigate/events", "frigate/other")


def test_frigate_detector_tracks_objects_of_its_camera():
    bus = FakeBus()
    det = FrigateDetector(bus, camera="frente", min_score=0.5)
    bus.inject("frigate/events", ev("new", "a"))
    bus.inject("frigate/events", ev("new", "b", camera="fondo"))
    out = det.detect()
    assert [d.label for d in out] == ["cat"] and out[0].bbox == (100, 200, 180, 300)
    bus.inject("frigate/events", ev("update", "a", box=(120, 200, 200, 300)))
    assert det.detect()[0].bbox == (120, 200, 200, 300)
    bus.inject("frigate/events", ev("end", "a"))
    assert det.detect() == []


def test_frigate_detector_drops_low_score_and_false_positives():
    bus = FakeBus()
    det = FrigateDetector(bus, camera="frente", min_score=0.5)
    bus.inject("frigate/events", ev("new", "a", score=0.3))
    assert det.detect() == []
    bus.inject("frigate/events", ev("new", "b"))
    bus.inject("frigate/events", ev("update", "b", false_positive=True))
    assert det.detect() == []


def test_frigate_detector_forgets_stale_objects():
    det = FrigateDetector(FakeBus(), camera="frente", stale_s=1.0)
    det.ingest(ev("new", "a"), now=-10.0)
    assert det.detect() == []


def test_mqtt_switch_publishes_on_and_off():
    import time

    bus = FakeBus()
    sw = MqttSwitch("luz", bus, topic="nodo/switch/luz/command", max_on_s=5)
    sw.start(0.1)
    time.sleep(0.3)
    assert [(t, p) for t, p, _ in bus.published] == [
        ("nodo/switch/luz/command", "ON"), ("nodo/switch/luz/command", "OFF")]


def test_mqtt_turret_aims_and_opens_valve():
    bus = FakeBus()
    t = build_mqtt_turret("torreta", bus, {
        "topics": {"pan": "n/number/pan/command", "tilt": "n/number/tilt/command", "valve": "n/switch/bomba/command"},
        "calibration": {"pan": [[0, 150], [640, 30]], "tilt": [[100, 80], [480, 20]]},
        "limits": {"pan": [40, 140]},
    }, max_on=5.0, pulse={})
    t.aim(320, 290, ts=0.0)
    t.start(1.0)
    topics = [x[0] for x in bus.published]
    assert topics[:3] == ["n/number/pan/command", "n/number/tilt/command", "n/switch/bomba/command"]
    assert bus.published[0][1] == "90.0" and bus.published[2][1] == "ON"
    t.stop()
    assert bus.published[-1] == ("n/switch/bomba/command", "OFF", False)


def test_mqtt_binary_sensor_gates_on_payload():
    bus = FakeBus()
    s = MqttBinarySensor("nivel", bus, topic="n/binary_sensor/vacio/state", empty_payload="ON", gates=["torreta"])
    assert s.ok()
    bus.inject("n/binary_sensor/vacio/state", "ON")
    assert not s.ok()
    bus.inject("n/binary_sensor/vacio/state", "OFF")
    assert s.ok()


def test_central_example_configs_load_and_run_in_simulation(tmp_path):
    from fuera_gatos.config import load_config
    from fuera_gatos.pipeline import run

    for name in ("frente", "fondo", "techo"):
        cfg = load_config(f"examples/central/config.{name}.yaml")
        assert cfg.detector.backend == "frigate" and cfg.mqtt.host
        cfg.events.log_file = str(tmp_path / f"{name}.jsonl")
        cfg.events.save_snapshots = False
        bus = FakeBus()
        # Simular un gato visto por Frigate en la zona con agua y correr unos cuadros.
        assert run(cfg, simulate=True, max_frames=1, bus=bus) == 0
