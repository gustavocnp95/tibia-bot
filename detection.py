"""Detecção de estado via análise de pixels nas regiões capturadas."""
import numpy as np

GREEN_HP_MIN_PIXELS = 30
RED_ATTACK_MIN_PIXELS = 30

# Minimo de pixels conectados para considerar um blob como marker de check verde
GREEN_MARKER_MIN_SIZE = 3


def _green_hp_mask(bgra):
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (g > 160) & (r < 80) & (b < 80)


def _red_attack_mask(bgra):
    """Vermelho puro saturado da borda de ataque — exclui chamas
    laranja/avermelhadas dos sprites (ex: Infernoids)."""
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (r > 220) & (g < 30) & (b < 30)


def _green_check_mask(bgra):
    """Verde neon/saturado do ícone de check."""
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (g > 200) & (r < 60) & (b < 60)


def _red_nearby_mask(bgra):
    """Vermelho-ish permissivo pra pegar a borda circular do marker."""
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (r > 150) & (g < 100) & (b < 100)


def has_target_in_battle_list(bgra):
    if bgra is None:
        return False
    return int(_green_hp_mask(bgra).sum()) >= GREEN_HP_MIN_PIXELS


def is_attacking(bgra):
    if bgra is None:
        return False
    return int(_red_attack_mask(bgra).sum()) >= RED_ATTACK_MIN_PIXELS


def find_green_check_markers(bgra, min_size=GREEN_MARKER_MIN_SIZE, red_proximity=6):
    """Retorna (x, y) de cada blob verde-check que tem vermelho (borda do
    marker) num raio de `red_proximity` pixels. Grama (verde sem vermelho
    ao redor) é descartada."""
    if bgra is None:
        return []
    green = _green_check_mask(bgra)
    red = _red_nearby_mask(bgra)
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
            while stack:
                x, y = stack.pop()
                sum_x += x
                sum_y += y
                count += 1
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and green[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((nx, ny))
            if count < min_size:
                continue
            cx, cy = sum_x // count, sum_y // count
            ylo = max(0, cy - red_proximity)
            yhi = min(h, cy + red_proximity + 1)
            xlo = max(0, cx - red_proximity)
            xhi = min(w, cx + red_proximity + 1)
            if red[ylo:yhi, xlo:xhi].any():
                centroids.append((cx, cy))
    return centroids
