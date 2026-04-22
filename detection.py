"""Detecção de estado via análise de pixels nas regiões capturadas."""
import numpy as np

GREEN_HP_MIN_PIXELS = 30
RED_ATTACK_MIN_PIXELS = 30

# Observado direto do mss em captura nativa 104x106:
# blob do ✓ = 26 px, bbox 7x7, avgRGB=(40, 142, 59). Em retina dobra.
GREEN_MARKER_MIN_SIZE = 15
# Qualquer blob bem maior que o ✓ é fundo/grama que por acaso casou a cor.
GREEN_MARKER_MAX_SIZE = 250
# Tiras estreitas de anti-aliasing na borda aparecem com largura=2.
GREEN_MARKER_MIN_BBOX_DIM = 4


def _green_hp_mask(bgra):
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (g > 160) & (r < 80) & (b < 80)


def _red_attack_mask(bgra):
    """Vermelho puro saturado da borda de ataque — exclui chamas
    laranja/avermelhadas dos sprites (ex: Infernoids)."""
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (r > 220) & (g < 30) & (b < 30)


def _green_check_mask(bgra):
    """Verde do ícone de ✓ — 3 tons observados no mss:
    (47,135,59), (68,206,87), (8,98,36). Todos têm R>=5 E B>=20,
    o que distingue da grama neon pura (0,204,0) e grama escura
    (0,90,30) — ambas com R=0 E B=0."""
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (
        (r >= 5) & (r <= 120)
        & (g >= 90) & (g <= 220)
        & (b >= 20) & (b <= 130)
        & (g.astype(np.int16) - r.astype(np.int16) >= 20)
        & (g.astype(np.int16) - b.astype(np.int16) >= 20)
    )


def has_target_in_battle_list(bgra):
    if bgra is None:
        return False
    return int(_green_hp_mask(bgra).sum()) >= GREEN_HP_MIN_PIXELS


def is_attacking(bgra):
    if bgra is None:
        return False
    return int(_red_attack_mask(bgra).sum()) >= RED_ATTACK_MIN_PIXELS


def find_green_check_markers(
    bgra,
    min_size=GREEN_MARKER_MIN_SIZE,
    max_size=GREEN_MARKER_MAX_SIZE,
    min_bbox_dim=GREEN_MARKER_MIN_BBOX_DIM,
):
    """Retorna (x, y) de cada ícone de ✓ no minimap. A cor do traço
    do check é bem distinta da grama neon, então não precisa de
    red-ring. Filtros extras rejeitam tiras de anti-aliasing e blobs
    grandes demais (grama que casa por acaso)."""
    if bgra is None:
        return []
    green = _green_check_mask(bgra)
    h, w = green.shape
    visited = np.zeros((h, w), dtype=bool)
    centroids = []
    for y0 in range(h):
        for x0 in range(w):
            if not green[y0, x0] or visited[y0, x0]:
                continue
            stack = [(x0, y0)]
            visited[y0, x0] = True
            sum_x = sum_y = count = 0
            min_x = max_x = x0
            min_y = max_y = y0
            while stack:
                x, y = stack.pop()
                sum_x += x
                sum_y += y
                count += 1
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and green[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((nx, ny))
            if count < min_size or count > max_size:
                continue
            if min(max_x - min_x + 1, max_y - min_y + 1) < min_bbox_dim:
                continue
            centroids.append((sum_x // count, sum_y // count))
    return centroids
