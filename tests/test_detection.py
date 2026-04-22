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
    # borda vermelha retangular (BGRA: B=0, G=0, R=240)
    for sl in (
        (slice(10, 12), slice(10, 140)),
        (slice(40, 42), slice(10, 140)),
        (slice(10, 42), slice(10, 12)),
        (slice(10, 42), slice(138, 140)),
    ):
        img[sl[0], sl[1], 0] = 0
        img[sl[0], sl[1], 1] = 0
        img[sl[0], sl[1], 2] = 240
    assert is_attacking(img) is True


def test_is_attacking_false_on_orange_flame_sprites():
    """Pixels alaranjados (chamas de Infernoids) não devem disparar is_attacking."""
    img = _blank_bgra()
    # chama laranja saturada: R=230 mas G=100 (tem componente verde) e B=30
    img[10:120, 10:120, 0] = 30
    img[10:120, 10:120, 1] = 100
    img[10:120, 10:120, 2] = 230
    assert is_attacking(img) is False


def _minimap_bgra(h=100, w=100):
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[:, :, 3] = 255
    # cinza neutro, como chão do minimap Tibia
    img[:, :, 0] = 102
    img[:, :, 1] = 102
    img[:, :, 2] = 102
    return img


def _paint_marker(img, cx, cy, size=5):
    """Pinta pixels da cor do traço do ✓ (verde-oliva: R=70, G=160, B=70)
    formando um bloco size×size — cobre o min_size=15 do detector."""
    half = size // 2
    img[cy - half:cy + half + 1, cx - half:cx + half + 1, 0] = 70   # B
    img[cy - half:cy + half + 1, cx - half:cx + half + 1, 1] = 160  # G
    img[cy - half:cy + half + 1, cx - half:cx + half + 1, 2] = 70   # R


def test_find_markers_empty_on_blank_minimap():
    img = _minimap_bgra()
    assert find_green_check_markers(img) == []


def test_find_markers_detects_single_marker():
    img = _minimap_bgra()
    _paint_marker(img, 50, 50)
    markers = find_green_check_markers(img)
    assert len(markers) == 1
    x, y = markers[0]
    assert abs(x - 50) <= 1 and abs(y - 50) <= 1


def test_find_markers_detects_multiple_markers():
    img = _minimap_bgra()
    _paint_marker(img, 20, 20)
    _paint_marker(img, 70, 30)
    _paint_marker(img, 40, 80)
    markers = find_green_check_markers(img)
    assert len(markers) == 3


def test_find_markers_ignores_dark_olive_grass():
    """Grama/verde escuro uniforme do minimap não deve virar marker."""
    img = _minimap_bgra()
    img[10:80, 10:80, 1] = 130
    img[10:80, 10:80, 2] = 40
    assert find_green_check_markers(img) == []


def test_find_markers_returns_empty_on_none():
    assert find_green_check_markers(None) == []


def test_find_markers_ignores_pure_neon_grass():
    """Grama neon pura (RGB ~0,200,0) é MUITO mais saturada que o traço
    do ✓ (oliva/teal) — a máscara do check não casa com ela."""
    img = _minimap_bgra()
    img[30:70, 30:70, 0] = 0     # B
    img[30:70, 30:70, 1] = 210   # G
    img[30:70, 30:70, 2] = 0     # R
    assert find_green_check_markers(img) == []


def test_find_markers_ignores_thin_edge_strip():
    """Tiras estreitas (ex: anti-aliasing na borda direita do minimap):
    bbox com largura < min_bbox_dim deve ser rejeitada mesmo se
    a contagem de pixels bater o min_size."""
    img = _minimap_bgra()
    # coluna de 20px altura x 2px largura com a cor do check
    img[10:30, 98:100, 0] = 70
    img[10:30, 98:100, 1] = 160
    img[10:30, 98:100, 2] = 70
    assert find_green_check_markers(img) == []
