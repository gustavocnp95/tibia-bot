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
    # fundo "grama" verde escuro/olive (não deve ser detectado)
    img[:, :, 1] = 90   # G moderado
    img[:, :, 2] = 50   # R baixo
    img[:, :, 0] = 30   # B baixo
    return img


def _paint_green_check(img, cx, cy, size=3):
    """Pinta pixels verde-neon (G=230, R=20, B=20)."""
    half = size // 2
    img[cy - half:cy + half + 1, cx - half:cx + half + 1, 0] = 20
    img[cy - half:cy + half + 1, cx - half:cx + half + 1, 1] = 230
    img[cy - half:cy + half + 1, cx - half:cx + half + 1, 2] = 20


def _paint_red_ring(img, cx, cy, radius=5):
    """Pinta borda/ring vermelho ao redor (R=200, G=30, B=30)."""
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            # apenas anel: distância ~ radius
            d = (dx * dx + dy * dy) ** 0.5
            if radius - 1.5 <= d <= radius + 0.5:
                y, x = cy + dy, cx + dx
                if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
                    img[y, x, 0] = 30
                    img[y, x, 1] = 30
                    img[y, x, 2] = 200


def _paint_marker(img, cx, cy):
    _paint_green_check(img, cx, cy, size=3)
    _paint_red_ring(img, cx, cy, radius=5)


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
    """Grama/verde escuro do minimap não deve virar marker."""
    img = _minimap_bgra()
    img[10:80, 10:80, 1] = 130
    img[10:80, 10:80, 2] = 40
    assert find_green_check_markers(img) == []


def test_find_markers_ignores_bright_green_without_red_ring():
    """Verde neon SEM vermelho ao redor (ex: tile de grama muito iluminado)
    não deve virar marker — precisa do ring vermelho pra confirmar."""
    img = _minimap_bgra()
    _paint_green_check(img, 50, 50, size=4)
    assert find_green_check_markers(img) == []


def test_find_markers_ignores_green_adjacent_to_lava_edge():
    """Aresta grama-lava: verde com vermelho só em um lado (não ring
    completo). Não deve virar marker."""
    img = _minimap_bgra()
    _paint_green_check(img, 50, 50, size=4)
    # vermelho tipo lava apenas no lado leste (um dos 4 lados)
    img[44:56, 56:70, 0] = 30
    img[44:56, 56:70, 1] = 30
    img[44:56, 56:70, 2] = 200
    assert find_green_check_markers(img) == []


def test_find_markers_returns_empty_on_none():
    assert find_green_check_markers(None) == []
