"""Carregamento/salvamento de configuração do bot."""
import json
import os

CONFIG_PATH = "config.json"


def default_config():
    return {
        "battle_list": None,   # {"x","y","width","height"} ou None
        "minimap": None,       # região do minimap onde procurar markers check verdes
        "walk_delay_min": 1.5, # segundos antes de próxima ação após clicar marker
        "walk_delay_max": 3.0,
    }


def load_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        return default_config()
    with open(path) as f:
        data = json.load(f)
    merged = default_config()
    merged.update(data)
    return merged


def save_config(cfg, path=CONFIG_PATH):
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
