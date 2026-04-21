"""Máquina de estados e loop principal do bot."""
import random
import threading
import time

import capture
import detection
import actions as act
from config import load_config


class Bot:
    def __init__(self, is_attacking, has_target, press_space, loot, click,
                 sleep, choose_marker, walk_delay, get_markers):
        self._is_attacking = is_attacking
        self._has_target = has_target
        self._press_space = press_space
        self._loot = loot
        self._click = click
        self._sleep = sleep
        self._choose_marker = choose_marker
        self._walk_delay = walk_delay
        self._get_markers = get_markers
        self.was_attacking = False

    def tick(self):
        if self._is_attacking():
            self.was_attacking = True
            self._sleep(0.15)
            return

        if self.was_attacking:
            self._loot()
            self.was_attacking = False
            self._sleep(0.6)
            return

        if self._has_target():
            self._press_space()
            self._sleep(0.4)
            return

        markers = self._get_markers()
        if not markers:
            self._sleep(0.3)
            return
        m = self._choose_marker(markers)
        self._click(m["x"], m["y"])
        self._sleep(self._walk_delay())


# ── Integração com hardware real ─────────────────────────────────────────────

class BotRunner:
    """Roda o Bot em thread dedicada, usando config + captura de tela reais."""

    def __init__(self, cfg_provider, log_fn=print):
        self._cfg_provider = cfg_provider  # callable -> cfg dict atualizado
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

    def _get_markers(self):
        return self._cfg_provider().get("markers", [])

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
            get_markers=self._get_markers,
        )
        while not self._stop.is_set():
            try:
                bot.tick()
            except Exception as e:
                self._log(f"erro no tick: {e}")
                time.sleep(0.5)

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
