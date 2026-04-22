"""Máquina de estados e loop principal do bot."""
import random
import threading
import time

import capture
import detection
import actions as act


class Bot:
    def __init__(self, is_attacking, has_target, press_space, loot, click,
                 sleep, choose_marker, walk_delay, find_markers, now=None):
        self._is_attacking = is_attacking
        self._has_target = has_target
        self._press_space = press_space
        self._loot = loot
        self._click = click
        self._sleep = sleep
        self._choose_marker = choose_marker
        self._walk_delay = walk_delay
        self._find_markers = find_markers
        self._now = now or time.monotonic
        self.was_attacking = False
        self._walk_cooldown_until = 0.0

    def tick(self):
        if self._is_attacking():
            self.was_attacking = True
            self._sleep(0.15)
            return

        if self.was_attacking:
            self._loot()
            self.was_attacking = False
            self._sleep(0.3)
            # flui para has_target: ataca o próximo imediatamente se remanescente

        if self._has_target():
            self._press_space()
            self._walk_cooldown_until = 0.0  # cancela o walk pendente
            self._sleep(0.4)
            return

        # cooldown não-bloqueante do walk — continua ticando rápido pra pegar
        # alvo que apareça no meio do caminho
        if self._now() < self._walk_cooldown_until:
            self._sleep(0.15)
            return

        markers = self._find_markers()
        if not markers:
            self._sleep(0.3)
            return
        m = self._choose_marker(markers)
        self._click(m[0], m[1])
        self._walk_cooldown_until = self._now() + self._walk_delay()


class BotRunner:
    """Roda o Bot em thread dedicada, usando config + captura de tela reais."""

    def __init__(self, cfg_provider, log_fn=print):
        self._cfg_provider = cfg_provider
        self._log = log_fn
        self._thread = None
        self._stop = threading.Event()

    def _is_attacking(self):
        cfg = self._cfg_provider()
        img = capture.grab_region(cfg.get("battle_list"))
        return detection.is_attacking(img)

    def _has_target(self):
        cfg = self._cfg_provider()
        img = capture.grab_region(cfg.get("battle_list"))
        return detection.has_target_in_battle_list(img)

    def _walk_delay(self):
        cfg = self._cfg_provider()
        return random.uniform(cfg.get("walk_delay_min", 1.5),
                              cfg.get("walk_delay_max", 3.0))

    def _find_markers(self):
        cfg = self._cfg_provider()
        region = cfg.get("minimap")
        if not region:
            return []
        img = capture.grab_region(region)
        if img is None:
            return []
        local = detection.find_green_check_markers(img)
        if not local:
            return []
        # compensa escala Retina: imagem vem em pixels nativos, mouse usa
        # coordenadas lógicas
        img_h, img_w = img.shape[:2]
        logical_w = max(1, int(region["width"]))
        logical_h = max(1, int(region["height"]))
        sx = img_w / logical_w
        sy = img_h / logical_h
        ox, oy = int(region["x"]), int(region["y"])
        return [(ox + int(x / sx), oy + int(y / sy)) for x, y in local]

    def _loop(self):
        bot = Bot(
            is_attacking=self._is_attacking,
            has_target=self._has_target,
            press_space=lambda: (self._log("space"), act.press_space()),
            loot=lambda: (self._log("loot (alt+q)"), act.loot_alt_q()),
            click=lambda x, y: (self._log(f"click {x},{y}"), act.click_at(x, y)),
            sleep=time.sleep,
            choose_marker=random.choice,
            walk_delay=self._walk_delay,
            find_markers=self._find_markers,
        )
        last_heartbeat = 0.0
        while not self._stop.is_set():
            try:
                bot.tick()
                now = time.monotonic()
                if now - last_heartbeat >= 3.0:
                    self._emit_heartbeat()
                    last_heartbeat = now
            except Exception as e:
                self._log(f"erro no tick: {e}")
                time.sleep(0.5)

    def _emit_heartbeat(self):
        cfg = self._cfg_provider()
        bl_img = capture.grab_region(cfg.get("battle_list"))
        mm_img = capture.grab_region(cfg.get("minimap"))
        has_t = detection.has_target_in_battle_list(bl_img)
        is_a = detection.is_attacking(bl_img)
        n_markers = len(detection.find_green_check_markers(mm_img)) if mm_img is not None else 0
        self._log(f"[hb] has_target={has_t} is_attacking={is_a} markers={n_markers}")

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._log("bot iniciado")

    def stop(self):
        self._stop.set()
        self._log("bot parado")

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()
