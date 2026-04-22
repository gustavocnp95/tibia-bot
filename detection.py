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
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (r > 180) & (g < 80) & (b < 80)


def _green_check_mask(bgra):
    """Verde neon/saturado do ícone de check — mais estrito que grama do minimap."""
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (g > 200) & (r < 60) & (b < 60)


def has_target_in_battle_list(bgra):
    if bgra is None:
        return False
    return int(_green_hp_mask(bgra).sum()) >= GREEN_HP_MIN_PIXELS


def is_attacking(bgra):
    if bgra is None:
        return False
    return int(_red_attack_mask(bgra).sum()) >= RED_ATTACK_MIN_PIXELS


def find_green_check_markers(bgra, min_size=GREEN_MARKER_MIN_SIZE):
    """Retorna lista de (x, y) em coords locais da imagem — centroides de cada
    blob de verde-check conectado (4-connectivity) com tamanho >= min_size."""
    if bgra is None:
        return []
    mask = _green_check_mask(bgra)
    h, w = mask.shape
    visited = np.zeros((h, w), dtype=bool)
    centroids = []
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0, x0] or visited[y0, x0]:
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
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((nx, ny))
            if count >= min_size:
                centroids.append((sum_x // count, sum_y // count))
    return centroids
