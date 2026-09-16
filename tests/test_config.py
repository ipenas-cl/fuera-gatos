import pytest
import yaml

from fuera_gatos.config import ConfigError, config_from_dict, load_config


def test_example_config_loads():
    cfg = load_config("config.example.yaml")
    assert cfg.detector.backend == "yolo"
    assert [z.name for z in cfg.zones] == ["basura", "jardin", "techo"]
    assert [lv.name for lv in cfg.controller.escalation] == ["nivel_1", "nivel_2"]
    assert cfg.controller.quiet_hours.allowed == ["luz", "ultrasonido", "aspersor"]
    assert cfg.deterrents["aspersor"].options["max_on_s"] == 5


def test_unknown_deterrent_in_level_is_rejected():
    raw = yaml.safe_load(open("config.example.yaml"))
    raw["controller"]["escalation"][0]["deterrents"].append("laser")
    with pytest.raises(ConfigError, match="laser"):
        config_from_dict(raw)


def test_excessive_duration_is_rejected():
    raw = yaml.safe_load(open("config.example.yaml"))
    raw["controller"]["escalation"][0]["duration_s"] = 120
    with pytest.raises(ConfigError, match="duration_s"):
        config_from_dict(raw)


def test_defaults_when_sections_missing():
    cfg = config_from_dict({"deterrents": {"luz": {"type": "log"}, "sonido": {"type": "log"}}})
    assert cfg.detector.backend == "motion"
    assert cfg.zones == []
    assert cfg.controller.escalation[0].deterrents == ["luz", "sonido"]


def test_level_referencing_missing_deterrent_fails_even_with_defaults():
    with pytest.raises(ConfigError, match="sonido"):
        config_from_dict({"deterrents": {"luz": {"type": "log"}}})


def test_example_multi_camera_configs_load():
    for name in ("examples/config.frente.yaml", "examples/config.fondo.yaml"):
        cfg = load_config(name)
        roof = next(z for z in cfg.zones if z.name.startswith("techo"))
        assert "aspersor" not in (roof.deterrents or [])
        assert "luz" in roof.deterrents


def test_zone_with_unknown_deterrent_is_rejected():
    raw = yaml.safe_load(open("config.example.yaml"))
    raw["zones"]["include"][0]["deterrents"] = ["canon"]
    with pytest.raises(ConfigError, match="canon"):
        config_from_dict(raw)
