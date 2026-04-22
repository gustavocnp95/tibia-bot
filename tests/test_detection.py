import numpy as np
from detection import (
    has_target_in_battle_list,
    is_attacking,
    find_green_check_markers,
)


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


def _minimap_bgra(h=100, w=100):
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[:, :, 3] = 255
    # fundo "grama" verde escuro/olive (não deve ser detectado)
    img[:, :, 1] = 90   # G moderado
    img[:, :, 2] = 50   # R baixo
    img[:, :, 0] = 30   # B baixo
    return img


def _paint_green_check(img, cx, cy, size=3):
    """Pinta um quadrado de pixels verde-neon (G=230, R=20, B=20)."""
    half = size // 2
    img[cy - half:cy + half + 1, cx - half:cx + half + 1, 0] = 20
    img[cy - half:cy + half + 1, cx - half:cx + half + 1, 1] = 230
    img[cy - half:cy + half + 1, cx - half:cx + half + 1, 2] = 20


def test_find_markers_empty_on_blank_minimap():
    img = _minimap_bgra()
    assert find_green_check_markers(img) == []


def test_find_markers_detects_single_marker():
    img = _minimap_bgra()
    _paint_green_check(img, 50, 50, size=3)
    markers = find_green_check_markers(img)
    assert len(markers) == 1
    x, y = markers[0]
    assert abs(x - 50) <= 1 and abs(y - 50) <= 1


def test_find_markers_detects_multiple_markers():
    img = _minimap_bgra()
    _paint_green_check(img, 20, 20, size=3)
    _paint_green_check(img, 70, 30, size=3)
    _paint_green_check(img, 40, 80, size=3)
    markers = find_green_check_markers(img)
    assert len(markers) == 3


def test_find_markers_ignores_dark_olive_grass():
    """Grama/verde escuro do minimap não deve virar marker."""
    img = _minimap_bgra()
    # grande área de verde escuro (não passa no threshold neon)
    img[10:80, 10:80, 1] = 130  # G médio
    img[10:80, 10:80, 2] = 40
    assert find_green_check_markers(img) == []


def test_find_markers_returns_empty_on_none():
    assert find_green_check_markers(None) == []
