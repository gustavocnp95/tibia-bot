"""
farm.py — attack + heal + mana automáticos

Attack: detecta inimigos na battle list, clica pra atacar e solta a tecla de ataque
Heal:   HP < 90% → spell (se ícone pronto e tem mana) ou potion (se ícone pronto)
Mana:   mana zerada → mana potion (se ícone pronto)

Cooldown: lê o ícone da hotkey na tela — brilhante = pronto, escuro = em cooldown
Controles: UI = configurar/ligar/desligar | Scroll-click = pausar/retomar
"""

import time
import json
import random
import threading
from collections import deque
import tkinter as tk
from tkinter import font as tkfont
from pynput import mouse
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Controller as MouseController, Button
import mss
import numpy as np

CONFIG_PATH = "config.json"

with open(CONFIG_PATH) as f:
    config = json.load(f)

kbd = KeyboardController()
mse = MouseController()

SPECIAL_KEYS = {
    "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
    "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
    "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
    "space": Key.space,
    "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
}

def press_key(key_str):
    key = SPECIAL_KEYS.get(key_str.lower(), key_str)
    kbd.press(key)
    time.sleep(0.05)
    kbd.release(key)

def save_config():
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


# ─── Screen capture ───────────────────────────────────────────────────────────

def _grab(region):
    with mss.mss() as sct:
        return np.array(sct.grab(region))

def _region(config_key):
    b = config.get(config_key)
    if not b:
        return None
    return {"left": int(b["x"]), "top": int(b["y"]),
            "width": int(b["width"]), "height": int(b["height"])}


# ─── Cooldown: lê brilho do ícone da hotkey ───────────────────────────────────

def is_ready(icon_config_key):
    """True se o ícone da skill está brilhante (fora de cooldown).
    Se não calibrado, assume pronto."""
    reg = _region(icon_config_key)
    if not reg:
        return True
    img = _grab(reg)
    brightness = np.mean(img[:, :, :3].astype(np.float32))
    return brightness > 70


# ─── Detecção de movimento por frame ─────────────────────────────────────────

def detect_tile_shift(frame1, frame2, tile_size=32):
    """Compara dois frames e retorna (fdx, fdy) em tiles do FRAME (não do char).
    Movimento do char = (-fdx, -fdy). Retorna (0,0) se não confiável."""
    h, w = frame1.shape[:2]
    patch = frame1[:50, :50, :3].astype(np.int32)
    best_score, best = float('inf'), (0, 0)
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            oy, ox = dy * tile_size, dx * tile_size
            y1, y2, x1, x2 = oy, oy + 50, ox, ox + 50
            if 0 <= y1 and y2 <= h and 0 <= x1 and x2 <= w:
                score = np.mean(np.abs(frame2[y1:y2, x1:x2, :3].astype(np.int32) - patch))
                if score < best_score:
                    best_score, best = score, (dx, dy)
    return best if best_score < 25 else (0, 0)


_RETRACE_KEYS = {
    (1,  0): Key.right,
    (-1, 0): Key.left,
    (0,  1): Key.down,
    (0, -1): Key.up,
}

def retrace_path(move_log, tile_size=32):
    """Pressiona teclas em ordem inversa para desfazer o caminho do combate."""
    step_delay = config.get("retrace_step_delay", 0.4)
    for char_dx, char_dy in reversed(move_log):
        key = _RETRACE_KEYS.get((-char_dx, -char_dy))
        if key:
            kbd.press(key)
            time.sleep(0.05)
            kbd.release(key)
            time.sleep(step_delay)


# ─── HP / Mana via OCR ────────────────────────────────────────────────────────

def _bar_percent(config_key, color):
    """
    Calcula % da barra contando COLUNAS com pelo menos um pixel colorido.
    color="auto": detecta qualquer cor saturada (verde/amarelo/vermelho) contra fundo escuro — para HP.
    color="blue": detecta azul — para mana.
    """
    reg = _region(config_key)
    if not reg:
        return None
    img = _grab(reg)
    r = img[:, :, 2].astype(np.int32)
    g = img[:, :, 1].astype(np.int32)
    b = img[:, :, 0].astype(np.int32)

    if color == "auto":
        # Pixel saturado: canal dominante bem acima dos outros e brilhante o suficiente
        max_ch = np.maximum(np.maximum(r, g), b)
        min_ch = np.minimum(np.minimum(r, g), b)
        mask = (max_ch > 80) & ((max_ch - min_ch) > 40)
    else:  # blue
        mask = (b > 100) & (r < 100) & (b > r + 40) & (b > g + 20)

    filled_cols = int(np.sum(mask.any(axis=0)))
    total_cols  = img.shape[1]
    return (filled_cols / total_cols) * 100 if total_cols > 0 else None

def get_hp_percent():
    pct = _bar_percent("hp_bar", "auto")
    return pct if pct is not None else 100

def get_mana_percent():
    pct = _bar_percent("mana_bar", "blue")
    return pct if pct is not None else 100

def has_hp_calibration():
    return bool(config.get("hp_bar"))

def has_mana_calibration():
    return bool(config.get("mana_bar"))


# ─── Attack ───────────────────────────────────────────────────────────────────

def is_enemy_selected():
    """Retorna True se há um quadrado vermelho de seleção na battle list (inimigo já atacado)."""
    bl = config.get("battle_list")
    if not bl:
        return False
    # Verifica apenas a coluna do ícone (primeiros ~32px de largura)
    icon_w = min(32, int(bl["width"]))
    img = _grab({"left": int(bl["x"]), "top": int(bl["y"]),
                 "width": icon_w, "height": int(bl["height"])})
    r = img[:, :, 2].astype(np.int32)
    g = img[:, :, 1].astype(np.int32)
    b = img[:, :, 0].astype(np.int32)
    # Quadrado vermelho: R alto, G e B baixos
    red_mask = (r > 160) & (g < 60) & (b < 60)
    return int(red_mask.sum()) >= 8

def find_enemy():
    bl = config.get("battle_list")
    if not bl:
        return None
    img = _grab({"left": int(bl["x"]), "top": int(bl["y"]),
                 "width": int(bl["width"]), "height": int(bl["height"])})
    # Só escaneia a metade esquerda: onde ficam o ícone e o nome da criatura.
    # A metade direita contém as barras de HP/mana, que mudam de cor (verde→amarelo→vermelho)
    # e causariam detecção falsa.
    half_w = max(1, img.shape[1] // 2)
    region = img[:, :half_w, :]
    r = region[:, :, 2].astype(np.int32)
    g = region[:, :, 1].astype(np.int32)
    b = region[:, :, 0].astype(np.int32)
    mask = (
        ((g > 130) & (r < 100) & (b < 100)) |  # nome verde
        ((r > 170) & (g > 170) & (b < 80))  |  # nome amarelo
        ((r > 150) & (g < 80)  & (b < 80))      # nome/sprite vermelho (ex: spider hostil)
    )
    row_sums = mask.sum(axis=1)
    for row in range(img.shape[0]):
        if row_sums[row] >= 10:
            return (int(bl["x"]) + int(bl["width"]) // 2, int(bl["y"]) + row)
    return None

def click_enemy(x, y):
    prev = mse.position
    mse.position = (x, y)
    time.sleep(0.05)
    mse.click(Button.left)
    time.sleep(0.05)
    bl = config.get("battle_list")
    px, py = prev
    if bl and int(bl["x"]) <= px <= int(bl["x"]) + int(bl["width"]) and \
              int(bl["y"]) <= py <= int(bl["y"]) + int(bl["height"]):
        ga = config.get("game_area")
        mse.position = (int(ga["x"]) + int(ga["width"]) // 2,
                        int(ga["y"]) + int(ga["height"]) // 2) if ga else (960, 540)
    else:
        mse.position = prev


# ─── Navegação por minimapa ───────────────────────────────────────────────────

_minimap_dir = None  # (dx, dy) normalizado da última direção de movimento

def find_minimap_target():
    global _minimap_dir
    """Captura o minimapa, BFS a partir do centro (posição do char) pelos pixels
    andáveis (brilho > threshold) e retorna (tx, ty) de tela de um tile aleatório
    alcançável. Retorna None se minimapa não calibrado ou sem tiles encontrados."""
    mm = config.get("minimap")
    if not mm:
        return None
    reg = _region("minimap")
    img = _grab(reg)
    h, w = img.shape[:2]
    cx, cy = w // 2, h // 2

    threshold = config.get("minimap_floor_brightness", 40)
    floor_mask = np.max(img[:, :, :3], axis=2) > threshold

    if not floor_mask[cy, cx]:
        return None

    dist_min = config.get("minimap_walk_dist_min", 10)
    dist_max = config.get("minimap_walk_dist_max", 30)

    visited = np.zeros((h, w), dtype=bool)
    visited[cy, cx] = True
    queue = deque([(cx, cy)])
    reachable = []

    while queue:
        x, y = queue.popleft()
        dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
        if dist > dist_max:
            continue
        if dist >= dist_min:
            reachable.append((x, y))
        for ddx, ddy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + ddx, y + ddy
            if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx] and floor_mask[ny, nx]:
                visited[ny, nx] = True
                queue.append((nx, ny))

    if not reachable:
        return None

    # Priorizar tiles na direção atual (produto escalar > 0 = cone de ±90°)
    if _minimap_dir is not None:
        dir_x, dir_y = _minimap_dir
        forward = [(x, y) for x, y in reachable
                   if (x - cx) * dir_x + (y - cy) * dir_y > 0]
        candidates = forward if forward else reachable  # sem saída → muda direção
    else:
        candidates = reachable

    px, py = random.choice(candidates)

    # Atualizar direção após escolha
    mag = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
    if mag > 0:
        _minimap_dir = ((px - cx) / mag, (py - cy) / mag)

    return int(mm["x"]) + px, int(mm["y"]) + py


# ─── Loot ────────────────────────────────────────────────────────────────────

def _find_sparkle_corpses():
    """Retorna lista de (screen_x, screen_y) de tiles com sparkle branco (loot disponível)."""
    ga = config.get("game_area")
    if not ga:
        return []
    img = _grab(_region("game_area"))
    # Sparkle = pixels bem brancos/prata em fundo escuro
    b = img[:, :, 0].astype(np.int32)
    g = img[:, :, 1].astype(np.int32)
    r = img[:, :, 2].astype(np.int32)
    bright = (r > 210) & (g > 210) & (b > 210)
    tile = config.get("tile_size", 32)
    h, w = img.shape[:2]
    positions = []
    for row in range(0, h, tile):
        for col in range(0, w, tile):
            if int(np.sum(bright[row:row + tile, col:col + tile])) >= 8:
                sx = int(ga["x"]) + col + tile // 2
                sy = int(ga["y"]) + row + tile // 2
                positions.append((sx, sy))
    return positions


def _gold_mask(img):
    """Máscara BGR dos pixels amarelo-dourados de gold coins."""
    r = img[:, :, 2].astype(np.int32)
    g = img[:, :, 1].astype(np.int32)
    b = img[:, :, 0].astype(np.int32)
    # Gold: R alto, G médio-alto, B baixo  (amarelo-laranja)
    return (r > 160) & (g > 100) & (b < 70) & (r > g + 30) & (r > b + 100)


def _collect_gold_from_area():
    """Ctrl+clica em cada célula 32×32 da loot_area que tem pixels dourados."""
    reg = _region("loot_area")
    if not reg:
        return
    img = _grab(reg)
    mask = _gold_mask(img)
    if int(np.sum(mask)) == 0:
        return
    cell = 32
    h, w = img.shape[:2]
    for row in range(0, h, cell):
        for col in range(0, w, cell):
            if np.sum(mask[row:row + cell, col:col + cell]) > 8:
                px = int(reg["left"]) + col + cell // 2
                py = int(reg["top"])  + row + cell // 2
                prev = mse.position
                kbd.press(Key.ctrl)
                time.sleep(0.05)
                mse.position = (px, py)
                time.sleep(0.05)
                mse.click(Button.left)
                time.sleep(0.05)
                kbd.release(Key.ctrl)
                mse.position = prev
                time.sleep(0.35)
                # Re-capturar imagem para pegar próximo item atualizado
                img  = _grab(reg)
                mask = _gold_mask(img)


def _close_loot_containers():
    """Fecha todos os containers na loot_area clicando nos botões X.
    Escaneia da esquerda pra direita e de cima pra baixo procurando
    o padrão do botão X (pixel escuro rodeado de claro no topo-direito
    de cada janela de container)."""
    reg = _region("loot_area")
    if not reg:
        return
    img      = _grab(reg)
    h, w     = img.shape[:2]
    # Percorre em busca de linhas de header de container:
    # headers costumam ser ~20px de altura com cor média (marrom/cinza)
    # e ficam no topo de cada container empilhado.
    scan_y       = 0
    header_h     = 20
    min_gap      = 30    # mínimo de pixels entre dois headers clicados
    last_click_y = -999
    while scan_y < h - header_h:
        strip    = img[scan_y: scan_y + header_h, :, :]
        mean_lum = float(np.mean(strip[:, :, :3]))
        # Header de container: não totalmente escuro, não totalmente branco
        if 35 < mean_lum < 150 and (scan_y - last_click_y) > min_gap:
            # O X fica perto da borda direita, no meio vertical do header
            x_px = int(reg["left"]) + w - 8
            y_px = int(reg["top"])  + scan_y + header_h // 2
            prev = mse.position
            mse.position = (x_px, y_px)
            time.sleep(0.05)
            mse.click(Button.left)
            mse.position = prev
            time.sleep(0.15)
            last_click_y = scan_y
            scan_y      += header_h
        else:
            scan_y += 2


def loot_corpses():
    """Detecta cadáveres brilhando → abre → coleta gold → fecha containers."""
    ga = config.get("game_area")
    if not ga or not config.get("loot_area"):
        return

    # 1. Achar tiles com sparkle (corpos com loot)
    targets = _find_sparkle_corpses()

    # Fallback: se não achou sparkle, tenta tiles ao redor do centro
    if not targets:
        cx    = int(ga["x"]) + int(ga["width"])  // 2
        cy    = int(ga["y"]) + int(ga["height"]) // 2
        tile  = config.get("tile_size", 32)
        offsets = [
            (0,0),(0,-1),(0,1),(-1,0),(1,0),
            (-1,-1),(1,-1),(-1,1),(1,1),
        ]
        targets = [(cx + dx*tile, cy + dy*tile) for dx, dy in offsets]

    # 2. Para cada cadáver: abrir, coletar gold
    for tx, ty in targets:
        prev = mse.position
        mse.position = (tx, ty)
        time.sleep(0.05)
        mse.click(Button.left)
        time.sleep(0.1)
        mse.click(Button.left)   # double-click abre o cadáver
        mse.position = prev
        time.sleep(0.6)          # aguarda container aparecer
        _collect_gold_from_area()
        time.sleep(0.15)

    # 3. Fechar todos os containers abertos
    if targets:
        time.sleep(0.2)
        _close_loot_containers()


# ─── Loop principal ───────────────────────────────────────────────────────────

running = False
paused  = False
HEAL_THRESHOLD = 90


def run():
    last_click        = 0.0
    last_mana_pot     = 0.0
    last_walk         = 0.0
    MANA_COOLDOWN     = 8.0


    in_combat        = False
    last_enemy_seen  = 0.0   # timestamp da última vez que vimos um inimigo
    move_log         = []   # lista de (char_dx, char_dy) em tiles
    prev_frame       = None
    last_walk_frame  = None

    while running:
        if paused:
            time.sleep(0.2)
            continue

        now = time.time()

        # ── Heal
        heal_spell  = config.get("heal_spell",  "").strip()
        heal_potion = config.get("heal_potion", "").strip()
        if heal_enabled_var.get() and (heal_spell or heal_potion) and has_hp_calibration():
            hp         = get_hp_percent()
            mana_empty = get_mana_percent() < 5 if has_mana_calibration() else False
            root.after(0, ui_update_bars, hp, get_mana_percent() if has_mana_calibration() else None)

            if hp < HEAL_THRESHOLD:
                if heal_spell and not mana_empty and is_ready("heal_spell_icon"):
                    press_key(heal_spell)
                elif heal_potion and is_ready("heal_potion_icon"):
                    press_key(heal_potion)

        # ── Mana potion
        mana_potion = config.get("mana_potion", "").strip()
        if mana_enabled_var.get() and mana_potion and has_mana_calibration() and now - last_mana_pot >= MANA_COOLDOWN:
            mana_pct       = get_mana_percent()
            mana_threshold = config.get("mana_threshold", 5)
            root.after(0, ui_update_bars, get_hp_percent() if has_hp_calibration() else None, mana_pct)
            if mana_pct < mana_threshold and is_ready("mana_potion_icon"):
                press_key(mana_potion)
                last_mana_pot = now

        # ── Capturar frame atual para rastreamento de movimento
        ga_reg = _region("game_area")
        curr_frame = _grab(ga_reg) if ga_reg else None

        # ── Rastrear deslocamento se estiver em combate
        if in_combat and prev_frame is not None and curr_frame is not None:
            tile_size = config.get("tile_size", 32)
            fdx, fdy = detect_tile_shift(prev_frame, curr_frame, tile_size)
            if (fdx, fdy) != (0, 0):
                move_log.append((-fdx, -fdy))   # char move oposto ao frame

        prev_frame = curr_frame

        # ── Attack: se tem inimigo na battle list, clica e ataca. Senão, caminha.
        if attack_enabled_var.get():
            enemy = find_enemy()
        else:
            enemy = None

        if enemy:
            last_enemy_seen = now

            if not in_combat:
                in_combat  = True
                move_log   = []
                prev_frame = curr_frame

            # Clica só se não há seleção ativa (quadrado vermelho ausente)
            if not is_enemy_selected():
                click_enemy(*enemy)
                last_click = now

            attack_key = config.get("attack_key", "").strip()
            if attack_key and is_ready("attack_icon"):
                press_key(attack_key)
            time.sleep(0.15)

        else:
            # Sem inimigo por 1s → considera morto, faz loot e retrace
            if in_combat and (now - last_enemy_seen >= 1.0):
                in_combat = False
                if loot_enabled_var.get():
                    loot_corpses()
                tile_size = config.get("tile_size", 32)
                retrace_path(move_log, tile_size)
                move_log   = []
                prev_frame = None

            # Só anda se não há inimigo (confirma com segunda leitura)
            if not in_combat and not find_enemy():
                # Detectar trava: se passou o walk_delay e não moveu, reseta
                if last_walk_frame is not None and curr_frame is not None:
                    tile_size = config.get("tile_size", 32)
                    fdx, fdy  = detect_tile_shift(last_walk_frame, curr_frame, tile_size)
                    if (fdx, fdy) == (0, 0) and now - last_walk >= config.get("walk_delay", 2.0):
                        last_walk = 0.0
                        last_walk_frame = None

                walk_delay = config.get("walk_delay", 2.0)
                if now - last_walk >= walk_delay:
                    target = find_minimap_target()
                    if target:
                        tx, ty = target
                        prev_pos = mse.position
                        mse.position = (tx, ty)
                        time.sleep(0.05)
                        mse.click(Button.left)
                        mse.position = prev_pos
                        last_walk_frame = curr_frame
                        last_walk = now

            time.sleep(0.15)

    root.after(0, ui_update_status)


# ─── Calibração ───────────────────────────────────────────────────────────────

calibrating = None
_corner1    = None

CALIB_PAIRS = {
    "bl":       "battle_list",
    "hp":       "hp_bar",
    "mana":     "mana_bar",
    "hs_icon":  "heal_spell_icon",
    "hi_icon":  "heal_potion_icon",
    "mi_icon":  "mana_potion_icon",
    "atk_icon": "attack_icon",
    "mm":       "minimap",
    "loot":     "loot_area",
}


def start_calib(kind):
    global calibrating, _corner1
    calibrating = kind
    _corner1    = None
    ui_set_hint("Scroll-click no canto SUP-ESQ")


def on_mouse_click(x, y, button, pressed):
    global calibrating, _corner1, paused

    if not pressed or button != Button.middle:
        return

    if calibrating is None:
        if running:
            paused = not paused
            root.after(0, ui_update_status)
        return

    if _corner1 is None:
        _corner1 = (x, y)
        root.after(0, ui_set_hint, "Agora scroll-click no canto INF-DIR")
    else:
        x1, y1 = _corner1
        config_key = CALIB_PAIRS.get(calibrating)
        if config_key:
            config[config_key] = {
                "x": min(x, x1), "y": min(y, y1),
                "width": abs(x - x1), "height": abs(y - y1)
            }
            save_config()
        calibrating = None
        _corner1    = None
        root.after(0, ui_set_hint, "")
        root.after(0, ui_update_calib_labels)


mouse_listener = mouse.Listener(on_click=on_mouse_click)
mouse_listener.start()


# ─── Captura de tecla ─────────────────────────────────────────────────────────

MODIFIER_KEYSYMS = {
    "shift_l", "shift_r", "control_l", "control_r",
    "alt_l", "alt_r", "meta_l", "meta_r", "super_l", "super_r",
    "caps_lock", "num_lock", "scroll_lock",
}

def capture_key_for(config_key, on_done):
    def on_key(event):
        name = event.keysym.lower()
        if name in MODIFIER_KEYSYMS:
            return
        root.unbind("<KeyPress>")
        config[config_key] = name
        save_config()
        on_done(name)
    root.bind("<KeyPress>", on_key)
    root.focus_force()


# ─── UI ───────────────────────────────────────────────────────────────────────

BG     = "#1e1e1e"
FG     = "#e0e0e0"
ACCENT = "#4fc3f7"
GREEN  = "#66bb6a"
RED    = "#ef5350"
YELLOW = "#ffd54f"
MUTED  = "#888888"

root = tk.Tk()
root.title("Farm Bot")
root.configure(bg=BG)
root.resizable(False, False)

heal_enabled_var   = tk.BooleanVar(value=config.get("heal_enabled",   True))
mana_enabled_var   = tk.BooleanVar(value=config.get("mana_enabled",   True))
attack_enabled_var = tk.BooleanVar(value=config.get("attack_enabled", True))
loot_enabled_var   = tk.BooleanVar(value=config.get("loot_enabled",   False))

def on_section_toggle():
    config["heal_enabled"]   = heal_enabled_var.get()
    config["mana_enabled"]   = mana_enabled_var.get()
    config["attack_enabled"] = attack_enabled_var.get()
    config["loot_enabled"]   = loot_enabled_var.get()
    save_config()

title_font   = tkfont.Font(family="Helvetica", size=13, weight="bold")
section_font = tkfont.Font(family="Helvetica", size=10, weight="bold")
normal_font  = tkfont.Font(family="Helvetica", size=9)
status_font  = tkfont.Font(family="Helvetica", size=12, weight="bold")

_status_label = None
_calib_labels = {}
_hint_label   = None
_hp_pct_label   = None
_mana_pct_label = None
_key_btn_refs = {}  # config_key → Button widget


def ui_update_status():
    if running and paused:
        _status_label.config(text="PAUSADO", fg=YELLOW)
    elif running:
        _status_label.config(text="LIGADO",    fg=GREEN)
    else:
        _status_label.config(text="DESLIGADO", fg=RED)

def _region_text(key):
    r = config.get(key)
    return f"{int(r['width'])}x{int(r['height'])} @ ({int(r['x'])},{int(r['y'])})" if r else "não calibrado"

def ui_update_calib_labels():
    for key, lbl in _calib_labels.items():
        lbl.config(text=_region_text(key))

def ui_set_hint(text=""):
    _hint_label.config(text=text)

def ui_update_bars(hp=None, mana=None):
    if _hp_pct_label:
        _hp_pct_label.config(text=f"{hp:.1f}%" if hp is not None else "—")
    if _mana_pct_label:
        _mana_pct_label.config(text=f"{mana:.1f}%" if mana is not None else "—")

def separator(parent):
    tk.Frame(parent, bg="#333", height=1).pack(fill="x", padx=16, pady=8)

def section_label(parent, text):
    tk.Label(parent, text=text, font=section_font, bg=BG, fg=ACCENT).pack(anchor="w", padx=16, pady=(6, 2))

def section_label_with_check(parent, text, var):
    frame = tk.Frame(parent, bg=BG)
    frame.pack(fill="x", padx=16, pady=(6, 2))
    tk.Label(frame, text=text, font=section_font, bg=BG, fg=ACCENT).pack(side="left")
    tk.Checkbutton(frame, variable=var, command=on_section_toggle,
                   bg=BG, activebackground=BG, selectcolor="#37474f",
                   relief="flat", cursor="hand2").pack(side="right")

def flat_btn(parent, text, cmd, bg="#37474f", **kw):
    return tk.Button(parent, text=text, command=cmd,
                     bg=bg, fg="black", activebackground=bg, activeforeground="black",
                     relief="flat", cursor="hand2", padx=10, pady=6,
                     font=normal_font, **kw)

def calib_row(parent, label_text, config_key, calib_kind):
    frame = tk.Frame(parent, bg=BG)
    frame.pack(fill="x", padx=16, pady=(2, 0))
    lbl = tk.Label(frame, text=_region_text(config_key), bg=BG, fg=MUTED, font=normal_font)
    lbl.pack(side="left")
    _calib_labels[config_key] = lbl
    flat_btn(frame, label_text, lambda: start_calib(calib_kind)).pack(side="right")

def key_row(parent, label_text, config_key, icon_key=None, icon_kind=None):
    """Linha: [label] [tecla] [calibrar ícone?]"""
    frame = tk.Frame(parent, bg=BG)
    frame.pack(fill="x", padx=16, pady=(4, 2))

    tk.Label(frame, text=label_text, bg=BG, fg=FG, font=normal_font, width=14, anchor="w").pack(side="left")

    btn_ref = [None]
    current = (config.get(config_key) or "—").upper()

    def start():
        btn_ref[0].config(text="Pressione...", bg="#424242", fg=YELLOW)
        capture_key_for(config_key, done)

    def done(name):
        btn_ref[0].config(text=name.upper(), bg="#37474f", fg="black")

    b = tk.Button(frame, text=current, command=start,
                  bg="#37474f", fg="black", activebackground="#546e7a", activeforeground="black",
                  relief="flat", cursor="hand2", padx=10, pady=4, font=normal_font, width=6)
    b.pack(side="left", padx=(0, 6))
    btn_ref[0] = b
    _key_btn_refs[config_key] = b

    if icon_key and icon_kind:
        icon_lbl = tk.Label(frame, text=_region_text(icon_key), bg=BG, fg=MUTED, font=normal_font)
        icon_lbl.pack(side="left")
        _calib_labels[icon_key] = icon_lbl
        flat_btn(frame, "Calibrar ícone", lambda: start_calib(icon_kind)).pack(side="right")



HOTKEY_KEYS = ["attack_key", "heal_spell", "heal_potion", "mana_potion"]

def _clear_hotkeys():
    for k in HOTKEY_KEYS:
        config[k] = ""
    save_config()
    for k in HOTKEY_KEYS:
        btn = _key_btn_refs.get(k)
        if btn:
            btn.config(text="—")


def on_ligar():
    global running
    if not config.get("battle_list"):
        ui_set_hint("Calibre a battle list primeiro!")
        return
    if running:
        return
    running = True
    ui_update_status()
    threading.Thread(target=run, daemon=True).start()

def on_desligar():
    global running
    running = False
    ui_update_status()


# ── Layout ───────────────────────────────────────────────────────────────────

tk.Label(root, text="Farm Bot", font=title_font, bg=BG, fg=ACCENT).pack(pady=(14, 4))

frame_status = tk.Frame(root, bg=BG)
frame_status.pack()
tk.Label(frame_status, text="Status:", bg=BG, fg=FG, font=normal_font).pack(side="left")
_status_label = tk.Label(frame_status, text="DESLIGADO", font=status_font, bg=BG, fg=RED)
_status_label.pack(side="left", padx=(6, 0))

separator(root)

# ── Attack
section_label_with_check(root, "⚔  Attack", attack_enabled_var)
calib_row(root, "Calibrar", "battle_list", "bl")
key_row(root, "Tecla de ataque:", "attack_key", "attack_icon", "atk_icon")

separator(root)

# ── Heal
section_label_with_check(root, "❤  Heal  (< 90%)", heal_enabled_var)
key_row(root, "Spell de heal:",  "heal_spell",  "heal_spell_icon",  "hs_icon")
key_row(root, "Potion de heal:", "heal_potion", "heal_potion_icon", "hi_icon")
calib_row(root, "Calibrar texto HP", "hp_bar", "hp")
frame_hp_disp = tk.Frame(root, bg=BG)
frame_hp_disp.pack(fill="x", padx=16, pady=(2, 0))
tk.Label(frame_hp_disp, text="HP detectado:", bg=BG, fg=MUTED, font=normal_font).pack(side="left")
_hp_pct_label = tk.Label(frame_hp_disp, text="—", bg=BG, fg=GREEN, font=normal_font)
_hp_pct_label.pack(side="left", padx=(6, 0))

separator(root)

# ── Mana
section_label_with_check(root, "🔮  Mana", mana_enabled_var)
key_row(root, "Potion de mana:", "mana_potion", "mana_potion_icon", "mi_icon")
calib_row(root, "Calibrar texto Mana", "mana_bar", "mana")
frame_mana_disp = tk.Frame(root, bg=BG)
frame_mana_disp.pack(fill="x", padx=16, pady=(2, 0))
tk.Label(frame_mana_disp, text="Mana detectada:", bg=BG, fg=MUTED, font=normal_font).pack(side="left")
_mana_pct_label = tk.Label(frame_mana_disp, text="—", bg=BG, fg=ACCENT, font=normal_font)
_mana_pct_label.pack(side="left", padx=(6, 0))

frame_mana_thr = tk.Frame(root, bg=BG)
frame_mana_thr.pack(fill="x", padx=16, pady=(4, 0))
tk.Label(frame_mana_thr, text="Usar potion abaixo de:", bg=BG, fg=FG, font=normal_font).pack(side="left")
mana_thr_var = tk.StringVar(value=str(config.get("mana_threshold", 5)))
mana_thr_entry = tk.Entry(frame_mana_thr, textvariable=mana_thr_var, width=5,
                           bg="#2d2d2d", fg="white", insertbackground="white",
                           relief="flat", font=normal_font, justify="center")
mana_thr_entry.pack(side="left", padx=(6, 4))
tk.Label(frame_mana_thr, text="%", bg=BG, fg=FG, font=normal_font).pack(side="left")

def on_mana_thr_change(*_):
    try:
        val = int(mana_thr_var.get())
        config["mana_threshold"] = max(0, min(100, val))
        save_config()
    except ValueError:
        pass

mana_thr_var.trace_add("write", on_mana_thr_change)

frame_clear_hotkeys = tk.Frame(root, bg=BG)
frame_clear_hotkeys.pack(fill="x", padx=16, pady=(6, 0))
flat_btn(frame_clear_hotkeys, "Limpar Hotkeys", _clear_hotkeys, bg="#5d4037").pack(side="right")

# Hint de calibração
_hint_label = tk.Label(root, text="", bg=BG, fg=YELLOW, font=normal_font)
_hint_label.pack(pady=(8, 0))

separator(root)

# ── Loot
section_label_with_check(root, "💰  Loot (gold)", loot_enabled_var)
calib_row(root, "Calibrar área de loot", "loot_area", "loot")

separator(root)

# ── Minimapa
section_label(root, "🗺  Minimapa")
calib_row(root, "Calibrar Minimapa", "minimap", "mm")

frame_mm_cfg = tk.Frame(root, bg=BG)
frame_mm_cfg.pack(fill="x", padx=16, pady=(6, 0))

tk.Label(frame_mm_cfg, text="Walk delay:", bg=BG, fg=FG, font=normal_font).pack(side="left")
walk_delay_var = tk.StringVar(value=str(config.get("walk_delay", 2.0)))
walk_delay_entry = tk.Entry(frame_mm_cfg, textvariable=walk_delay_var, width=4,
                            bg="#2d2d2d", fg="white", insertbackground="white",
                            relief="flat", font=normal_font, justify="center")
walk_delay_entry.pack(side="left", padx=(6, 2))
tk.Label(frame_mm_cfg, text="s", bg=BG, fg=FG, font=normal_font).pack(side="left", padx=(0, 12))

tk.Label(frame_mm_cfg, text="Brilho mín.:", bg=BG, fg=FG, font=normal_font).pack(side="left")
mm_brightness_var = tk.StringVar(value=str(config.get("minimap_floor_brightness", 40)))
mm_brightness_entry = tk.Entry(frame_mm_cfg, textvariable=mm_brightness_var, width=4,
                               bg="#2d2d2d", fg="white", insertbackground="white",
                               relief="flat", font=normal_font, justify="center")
mm_brightness_entry.pack(side="left", padx=(6, 2))

def on_walk_delay_change(*_):
    try:
        val = float(walk_delay_var.get())
        config["walk_delay"] = max(0.5, val)
        save_config()
    except ValueError:
        pass

def on_mm_brightness_change(*_):
    try:
        val = int(mm_brightness_var.get())
        config["minimap_floor_brightness"] = max(10, min(200, val))
        save_config()
    except ValueError:
        pass

walk_delay_var.trace_add("write", on_walk_delay_change)
mm_brightness_var.trace_add("write", on_mm_brightness_change)

separator(root)

# Ligar / Desligar
frame_btns = tk.Frame(root, bg=BG)
frame_btns.pack(pady=(2, 14))
flat_btn(frame_btns, "  Ligar  ", on_ligar,    bg="#2e7d32").pack(side="left", padx=(0, 8))
flat_btn(frame_btns, "Desligar",  on_desligar, bg="#c62828").pack(side="left")

tk.Label(root, text="Scroll-click = pausar / retomar", bg=BG, fg=MUTED, font=normal_font).pack(pady=(0, 12))

root.mainloop()
