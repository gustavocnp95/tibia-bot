import numpy as np
from detection import has_target_in_battle_list, is_attacking


def _blank_bgra(h=160, w=156):
    # fundo escuro cinza, BGRA
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[:, :, 3] = 255
    img[:, :, 0:3] = 40
    return img


def test_has_target_false_on_empty_battle_list():
    img = _blank_bgra()
    assert has_target_in_battle_list(img) is False


def test_has_target_true_when_hp_bar_present():
    img = _blank_bgra()
    # barra verde simulando HP bar (BGRA: B=40, G=200, R=40)
    img[20:22, 40:130, 0] = 40   # B
    img[20:22, 40:130, 1] = 200  # G
    img[20:22, 40:130, 2] = 40   # R
    assert has_target_in_battle_list(img) is True


def test_is_attacking_false_without_red():
    img = _blank_bgra()
    assert is_attacking(img) is False


def test_is_attacking_true_with_red_square_border():
    img = _blank_bgra()
    # borda vermelha retangular (BGRA: B=20, G=20, R=220)
    img[10:12, 10:140, 2] = 220
    img[40:42, 10:140, 2] = 220
    img[10:42, 10:12, 2] = 220
    img[10:42, 138:140, 2] = 220
    # confirmar B e G baixos (já estão)
    assert is_attacking(img) is True
