"""Detecção de estado via análise de pixels nas regiões capturadas."""
import numpy as np

# Threshold: numero mínimo de pixels que satisfazem a máscara
GREEN_HP_MIN_PIXELS = 30
RED_ATTACK_MIN_PIXELS = 30


def _green_hp_mask(bgra):
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (g > 160) & (r < 80) & (b < 80)


def _red_attack_mask(bgra):
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (r > 180) & (g < 80) & (b < 80)


def has_target_in_battle_list(bgra):
    if bgra is None:
        return False
    return int(_green_hp_mask(bgra).sum()) >= GREEN_HP_MIN_PIXELS


def is_attacking(bgra):
    if bgra is None:
        return False
    return int(_red_attack_mask(bgra).sum()) >= RED_ATTACK_MIN_PIXELS
