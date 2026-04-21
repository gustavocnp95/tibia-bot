import json
import os
from config import load_config, save_config, default_config


def test_load_returns_defaults_when_file_missing(tmp_path):
    path = tmp_path / "missing.json"
    cfg = load_config(str(path))
    assert cfg == default_config()


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    cfg = default_config()
    cfg["markers"] = [{"x": 100, "y": 200}, {"x": 300, "y": 400}]
    cfg["battle_list"] = {"x": 10, "y": 20, "width": 150, "height": 160}
    save_config(cfg, str(path))
    loaded = load_config(str(path))
    assert loaded["markers"] == cfg["markers"]
    assert loaded["battle_list"] == cfg["battle_list"]


def test_default_config_has_required_keys():
    cfg = default_config()
    assert "battle_list" in cfg
    assert "game_area" in cfg
    assert "markers" in cfg
    assert "walk_delay_min" in cfg
    assert "walk_delay_max" in cfg
    assert cfg["markers"] == []
