from config import load_config, save_config, default_config


def test_load_returns_defaults_when_file_missing(tmp_path):
    path = tmp_path / "missing.json"
    cfg = load_config(str(path))
    assert cfg == default_config()


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    cfg = default_config()
    cfg["minimap"] = {"x": 1600, "y": 70, "width": 100, "height": 100}
    cfg["battle_list"] = {"x": 10, "y": 20, "width": 150, "height": 160}
    save_config(cfg, str(path))
    loaded = load_config(str(path))
    assert loaded["minimap"] == cfg["minimap"]
    assert loaded["battle_list"] == cfg["battle_list"]


def test_default_config_has_required_keys():
    cfg = default_config()
    assert "battle_list" in cfg
    assert "minimap" in cfg
    assert "walk_delay_min" in cfg
    assert "walk_delay_max" in cfg
    assert cfg["battle_list"] is None
    assert cfg["minimap"] is None
