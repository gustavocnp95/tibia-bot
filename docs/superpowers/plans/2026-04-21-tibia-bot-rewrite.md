# Tibia Bot Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apagar o bot existente e construir um novo bot simples do Tibia (macOS) com 3 funções: (1) andar clicando em markers configurados aleatoriamente, (2) apertar espaço quando houver alvo na battle list e esperar matar, (3) apertar option+Q para lootear após cada kill.

**Architecture:** App Python single-process. Loop do bot roda em thread separada; UI tkinter na thread principal. Detecção via screen capture (mss) + análise de pixels (numpy) em duas regiões: battle list (presença de alvo + quadrado vermelho de ataque). Ações via pynput (teclado + mouse). Config persistida em JSON (regiões calibradas + lista de markers). Estados do bot: IDLE → ATTACKING → LOOTING → WALKING.

**Tech Stack:** Python 3.11+, tkinter (UI), mss (screen capture), numpy (pixel analysis), pynput (input), json (config). macOS (Darwin) — tecla "option" é mapeada como `Key.alt` no pynput.

---

## File Structure

Arquivos a serem criados (tudo novo, na raiz do projeto):

- `config.py` — carregamento/salvamento de `config.json`; esquema: regiões calibradas + lista de markers.
- `capture.py` — wrappers finos para mss (captura de região como numpy array).
- `detection.py` — funções puras que recebem numpy arrays e retornam booleanos: `has_target_in_battle_list()`, `is_attacking()`.
- `actions.py` — `press_space()`, `loot_alt_q()`, `click_at(x, y)`. Encapsula pynput.
- `bot.py` — máquina de estados + loop principal do bot (rodado em thread). Sem UI.
- `ui.py` — tkinter UI: calibrar regiões, gerenciar markers, start/stop, log. Ponto de entrada (`python ui.py`).
- `tests/test_detection.py` — testes unitários de detecção com arrays sintéticos.
- `tests/test_bot.py` — testes unitários da máquina de estados com mocks de detecção/ações.
- `config.json` — arquivo gerado pela UI em runtime (não versionado inicialmente).

Arquivos a serem removidos:

- `farm.py`
- `config.json` (atual)
- `waypoints.json`
- `__pycache__/`

Arquivos mantidos/atualizados:

- `requirements.txt` (mantém pynput, mss, numpy, Pillow; remove pytesseract).

---

### Task 1: Limpeza — apagar código antigo

**Files:**
- Delete: `farm.py`
- Delete: `config.json`
- Delete: `waypoints.json`
- Delete: `__pycache__/`
- Modify: `requirements.txt`

- [ ] **Step 1: Apagar arquivos antigos**

Run:
```bash
cd /Users/gustavonavarro/tibia-bot
rm -f farm.py config.json waypoints.json
rm -rf __pycache__
```
Expected: sem output, sem erros.

- [ ] **Step 2: Atualizar requirements.txt**

Conteúdo completo:
```
pynput
mss
numpy
Pillow
pytest
```

- [ ] **Step 3: Verificar venv e instalar deps**

Run:
```bash
cd /Users/gustavonavarro/tibia-bot
source .venv/bin/activate
pip install -r requirements.txt
```
Expected: instalação sem erros.

- [ ] **Step 4: Criar estrutura de pastas**

Run:
```bash
cd /Users/gustavonavarro/tibia-bot
mkdir -p tests
touch tests/__init__.py
```
Expected: pasta `tests/` criada.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove legacy bot code and prep clean slate"
```

---

### Task 2: Módulo de configuração

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Escrever teste falhando**

Arquivo `tests/test_config.py`:
```python
import json
import os
from config import load_config, save_config, default_config


def test_load_returns_defaults_when_file_missing(tmp_path):
    path = tmp_path / "missing.json"
    cfg = load_config(str(path))
    assert cfg == default_config()


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    cfg = default_config()
    cfg["markers"] = [{"x": 100, "y": 200}, {"x": 300, "y": 400}]
    cfg["battle_list"] = {"x": 10, "y": 20, "width": 150, "height": 160}
    save_config(cfg, str(path))
    loaded = load_config(str(path))
    assert loaded["markers"] == cfg["markers"]
    assert loaded["battle_list"] == cfg["battle_list"]


def test_default_config_has_required_keys():
    cfg = default_config()
    assert "battle_list" in cfg
    assert "game_area" in cfg
    assert "markers" in cfg
    assert "walk_delay_min" in cfg
    assert "walk_delay_max" in cfg
    assert cfg["markers"] == []
```

- [ ] **Step 2: Rodar teste e confirmar falha**

Run: `cd /Users/gustavonavarro/tibia-bot && source .venv/bin/activate && pytest tests/test_config.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'config'`.

- [ ] **Step 3: Implementar `config.py`**

```python
"""Carregamento/salvamento de configuração do bot."""
import json
import os

CONFIG_PATH = "config.json"


def default_config():
    return {
        "battle_list": None,   # {"x","y","width","height"} ou None
        "game_area": None,
        "markers": [],         # lista de {"x","y"} em coords de tela
        "walk_delay_min": 1.5, # segundos antes de próxima ação após clicar marker
        "walk_delay_max": 3.0,
        "attack_timeout": 8.0, # segundos máx esperando kill antes de re-avaliar
    }


def load_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        return default_config()
    with open(path) as f:
        data = json.load(f)
    merged = default_config()
    merged.update(data)
    return merged


def save_config(cfg, path=CONFIG_PATH):
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
```

- [ ] **Step 4: Rodar teste e confirmar sucesso**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py requirements.txt tests/__init__.py
git commit -m "feat: add config module with load/save/defaults"
```

---

### Task 3: Captura de tela (wrapper mss)

**Files:**
- Create: `capture.py`

- [ ] **Step 1: Implementar `capture.py`**

Não tem TDD útil aqui — é wrapper puro de biblioteca externa. Implementar direto e validar manualmente.

```python
"""Captura de regiões da tela como numpy arrays."""
import mss
import numpy as np


def grab_region(region):
    """Retorna ndarray BGRA (H,W,4). region = dict com x, y, width, height."""
    if region is None:
        return None
    bbox = {
        "left": int(region["x"]),
        "top": int(region["y"]),
        "width": int(region["width"]),
        "height": int(region["height"]),
    }
    with mss.mss() as sct:
        return np.array(sct.grab(bbox))
```

- [ ] **Step 2: Smoke test manual**

Run:
```bash
cd /Users/gustavonavarro/tibia-bot && source .venv/bin/activate
python -c "from capture import grab_region; a=grab_region({'x':0,'y':0,'width':100,'height':100}); print(a.shape, a.dtype)"
```
Expected: `(100, 100, 4) uint8`.

- [ ] **Step 3: Commit**

```bash
git add capture.py
git commit -m "feat: add mss screen capture wrapper"
```

---

### Task 4: Detecção — battle list e quadrado vermelho

**Files:**
- Create: `detection.py`
- Test: `tests/test_detection.py`

Estratégia: operar em arrays numpy BGRA. Funções puras, testáveis com arrays sintéticos.

- `has_target_in_battle_list(img)` — procura pixels de HP bar verde (R<80, G>160, B<80). Se a contagem > threshold, há alvo.
- `is_attacking(img)` — procura pixels vermelhos fortes (R>180, G<80, B<80) que indicam o retângulo vermelho de ataque. Contagem > threshold = atacando.

- [ ] **Step 1: Escrever testes falhando**

Arquivo `tests/test_detection.py`:
```python
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
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_detection.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'detection'`.

- [ ] **Step 3: Implementar `detection.py`**

```python
"""Detecção de estado via análise de pixels nas regiões capturadas."""
import numpy as np

# Threshold: numero mínimo de pixels que satisfazem a máscara
GREEN_HP_MIN_PIXELS = 30
RED_ATTACK_MIN_PIXELS = 30


def _green_hp_mask(bgra):
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (g > 160) & (r < 80) & (b < 80)


def _red_attack_mask(bgra):
    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]
    return (r > 180) & (g < 80) & (b < 80)


def has_target_in_battle_list(bgra):
    if bgra is None:
        return False
    return int(_green_hp_mask(bgra).sum()) >= GREEN_HP_MIN_PIXELS


def is_attacking(bgra):
    if bgra is None:
        return False
    return int(_red_attack_mask(bgra).sum()) >= RED_ATTACK_MIN_PIXELS
```

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_detection.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add detection.py tests/test_detection.py
git commit -m "feat: add battle list target + attacking detection"
```

---

### Task 5: Ações de input (teclado + mouse)

**Files:**
- Create: `actions.py`

Wrapper fino de pynput. Sem TDD — validação manual.

- [ ] **Step 1: Implementar `actions.py`**

```python
"""Ações de input: teclas e cliques."""
import time
from pynput.keyboard import Key, Controller as KB
from pynput.mouse import Button, Controller as MS

_kb = KB()
_ms = MS()


def press_space():
    _kb.press(Key.space)
    time.sleep(0.05)
    _kb.release(Key.space)


def loot_alt_q():
    """option+Q no macOS (Key.alt no pynput)."""
    _kb.press(Key.alt)
    time.sleep(0.03)
    _kb.press('q')
    time.sleep(0.05)
    _kb.release('q')
    time.sleep(0.03)
    _kb.release(Key.alt)


def click_at(x, y, button=Button.left):
    _ms.position = (int(x), int(y))
    time.sleep(0.05)
    _ms.click(button, 1)
```

- [ ] **Step 2: Smoke test sintático**

Run:
```bash
cd /Users/gustavonavarro/tibia-bot && source .venv/bin/activate
python -c "import actions; print('ok')"
```
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add actions.py
git commit -m "feat: add input actions (space, alt+q, click)"
```

---

### Task 6: Máquina de estados do bot

**Files:**
- Create: `bot.py`
- Test: `tests/test_bot.py`

A máquina de estados deve ser testável sem tela nem input reais. Design: classe `Bot` com dependências injetáveis (função de detecção, função de ação, função de sleep, função de random.choice para markers).

Comportamento por tick:
1. Se `is_attacking()` → está no meio do combate, marca `was_attacking=True`, dorme curto, retorna.
2. Se não está atacando e `was_attacking` era True → acabou de matar: chama `loot()`, zera `was_attacking`, dorme ~600ms, retorna.
3. Se `has_target()` → chama `press_space()`, dorme ~400ms, retorna.
4. Sem alvo: pick marker aleatório, `click(marker)`, dorme walk_delay aleatório entre min/max.

- [ ] **Step 1: Escrever testes falhando**

Arquivo `tests/test_bot.py`:
```python
from bot import Bot


class FakeEnv:
    def __init__(self):
        self.attacking = False
        self.has_target = False
        self.actions = []
        self.sleeps = []
        self.markers = [{"x": 100, "y": 200}, {"x": 300, "y": 400}]
        self._marker_choice_idx = 0

    def is_attacking(self):
        return self.attacking

    def has_target_in_battle_list(self):
        return self.has_target

    def press_space(self):
        self.actions.append(("space",))

    def loot(self):
        self.actions.append(("loot",))

    def click(self, x, y):
        self.actions.append(("click", x, y))

    def sleep(self, s):
        self.sleeps.append(s)

    def choose_marker(self, markers):
        m = markers[self._marker_choice_idx % len(markers)]
        self._marker_choice_idx += 1
        return m

    def walk_delay(self):
        return 2.0


def make_bot(env):
    return Bot(
        is_attacking=env.is_attacking,
        has_target=env.has_target_in_battle_list,
        press_space=env.press_space,
        loot=env.loot,
        click=env.click,
        sleep=env.sleep,
        choose_marker=env.choose_marker,
        walk_delay=env.walk_delay,
        get_markers=lambda: env.markers,
    )


def test_tick_presses_space_when_target_present():
    env = FakeEnv()
    env.has_target = True
    bot = make_bot(env)
    bot.tick()
    assert ("space",) in env.actions


def test_tick_waits_when_already_attacking():
    env = FakeEnv()
    env.attacking = True
    bot = make_bot(env)
    bot.tick()
    assert env.actions == []  # nenhuma ação nova
    assert bot.was_attacking is True


def test_tick_loots_after_kill():
    env = FakeEnv()
    bot = make_bot(env)
    # primeiro tick: atacando
    env.attacking = True
    bot.tick()
    # segundo tick: inimigo morreu (attacking=False, has_target=False)
    env.attacking = False
    env.has_target = False
    bot.tick()
    assert ("loot",) in env.actions
    assert bot.was_attacking is False


def test_tick_walks_to_marker_when_idle():
    env = FakeEnv()
    bot = make_bot(env)
    bot.tick()
    assert env.actions[0] == ("click", 100, 200)


def test_tick_no_walk_when_no_markers():
    env = FakeEnv()
    env.markers = []
    bot = make_bot(env)
    bot.tick()
    # sem alvo e sem markers → nenhuma ação de click
    assert all(a[0] != "click" for a in env.actions)


def test_does_not_loot_without_prior_attack():
    env = FakeEnv()
    bot = make_bot(env)
    # nunca esteve em attacking
    bot.tick()
    assert ("loot",) not in env.actions
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_bot.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'bot'`.

- [ ] **Step 3: Implementar `bot.py`**

```python
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
```

- [ ] **Step 4: Rodar testes e confirmar sucesso**

Run: `pytest tests/test_bot.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add bot.py tests/test_bot.py
git commit -m "feat: add bot state machine with injected dependencies"
```

---

### Task 7: UI — base, start/stop, log

**Files:**
- Create: `ui.py`

- [ ] **Step 1: Implementar esqueleto da UI**

```python
"""UI tkinter para configurar e controlar o bot."""
import tkinter as tk
from tkinter import ttk, messagebox
from pynput import mouse as pynput_mouse

from config import load_config, save_config
from bot import BotRunner


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Tibia Bot")
        self.root.geometry("520x600")
        self.cfg = load_config()
        self.runner = BotRunner(cfg_provider=lambda: self.cfg, log_fn=self.log)

        self._build_ui()
        self._refresh()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # ── Regiões calibradas
        regions_frame = ttk.LabelFrame(self.root, text="Regiões")
        regions_frame.pack(fill="x", **pad)
        self.battle_list_label = ttk.Label(regions_frame, text="Battle list: -")
        self.battle_list_label.pack(anchor="w", padx=6)
        ttk.Button(regions_frame, text="Calibrar battle list",
                   command=self._calibrate_battle_list).pack(anchor="w", padx=6, pady=2)

        # ── Markers
        markers_frame = ttk.LabelFrame(self.root, text="Markers (aleatórios)")
        markers_frame.pack(fill="both", expand=False, **pad)
        self.markers_list = tk.Listbox(markers_frame, height=8)
        self.markers_list.pack(fill="x", padx=6, pady=4)
        btns = ttk.Frame(markers_frame)
        btns.pack(fill="x")
        ttk.Button(btns, text="Adicionar marker (clique na tela)",
                   command=self._add_marker).pack(side="left", padx=6, pady=2)
        ttk.Button(btns, text="Remover selecionado",
                   command=self._remove_marker).pack(side="left", padx=6, pady=2)
        ttk.Button(btns, text="Limpar todos",
                   command=self._clear_markers).pack(side="left", padx=6, pady=2)

        # ── Delays
        delay_frame = ttk.LabelFrame(self.root, text="Walk delay (segundos)")
        delay_frame.pack(fill="x", **pad)
        self.delay_min_var = tk.DoubleVar(value=self.cfg["walk_delay_min"])
        self.delay_max_var = tk.DoubleVar(value=self.cfg["walk_delay_max"])
        ttk.Label(delay_frame, text="Min:").grid(row=0, column=0, padx=4, pady=2)
        ttk.Entry(delay_frame, textvariable=self.delay_min_var, width=8).grid(row=0, column=1)
        ttk.Label(delay_frame, text="Max:").grid(row=0, column=2, padx=4)
        ttk.Entry(delay_frame, textvariable=self.delay_max_var, width=8).grid(row=0, column=3)
        ttk.Button(delay_frame, text="Salvar", command=self._save_delays).grid(row=0, column=4, padx=6)

        # ── Start/Stop
        ctrl = ttk.Frame(self.root)
        ctrl.pack(fill="x", **pad)
        self.start_btn = ttk.Button(ctrl, text="Iniciar", command=self._start)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ttk.Button(ctrl, text="Parar", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        # ── Log
        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=12, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=4)

    def _refresh(self):
        bl = self.cfg.get("battle_list")
        if bl:
            self.battle_list_label.config(
                text=f"Battle list: x={bl['x']:.0f} y={bl['y']:.0f} "
                     f"w={bl['width']:.0f} h={bl['height']:.0f}")
        else:
            self.battle_list_label.config(text="Battle list: (não calibrada)")
        self.markers_list.delete(0, tk.END)
        for i, m in enumerate(self.cfg.get("markers", [])):
            self.markers_list.insert(tk.END, f"{i+1}: ({m['x']:.0f}, {m['y']:.0f})")

    def log(self, msg):
        self.root.after(0, self._append_log, str(msg))

    def _append_log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    # ── placeholders (implementados nas próximas tasks)
    def _calibrate_battle_list(self):
        messagebox.showinfo("TODO", "Será implementado na Task 8")

    def _add_marker(self):
        messagebox.showinfo("TODO", "Será implementado na Task 9")

    def _remove_marker(self):
        idx = self.markers_list.curselection()
        if not idx:
            return
        self.cfg["markers"].pop(idx[0])
        save_config(self.cfg)
        self._refresh()

    def _clear_markers(self):
        self.cfg["markers"] = []
        save_config(self.cfg)
        self._refresh()

    def _save_delays(self):
        self.cfg["walk_delay_min"] = float(self.delay_min_var.get())
        self.cfg["walk_delay_max"] = float(self.delay_max_var.get())
        save_config(self.cfg)
        self.log("delays salvos")

    def _start(self):
        if not self.cfg.get("battle_list"):
            messagebox.showerror("Erro", "Calibre a battle list primeiro.")
            return
        self.runner.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def _stop(self):
        self.runner.stop()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test da UI**

Run:
```bash
cd /Users/gustavonavarro/tibia-bot && source .venv/bin/activate
python ui.py
```
Expected: janela abre. Feche manualmente.

- [ ] **Step 3: Commit**

```bash
git add ui.py
git commit -m "feat: add tkinter UI skeleton with start/stop and log"
```

---

### Task 8: UI — calibração da battle list

**Files:**
- Modify: `ui.py`

Fluxo: usuário clica "Calibrar battle list". A janela esconde e entra em modo "clique no canto superior-esquerdo", depois "clique no canto inferior-direito". Guarda as duas coordenadas como bounding box.

- [ ] **Step 1: Substituir `_calibrate_battle_list` em `ui.py`**

Localizar o método `_calibrate_battle_list` em `ui.py` e substituir por:

```python
    def _calibrate_battle_list(self):
        self.log("calibrando battle list: clique no canto SUPERIOR-ESQUERDO")
        self.root.withdraw()
        self._capture_two_clicks(self._finish_battle_list_calibration)

    def _capture_two_clicks(self, on_done):
        """Captura duas posições do mouse em sequência."""
        clicks = []

        def on_click(x, y, button, pressed):
            if not pressed:
                return
            clicks.append((x, y))
            if len(clicks) == 1:
                self.root.after(0, self.log,
                                "agora clique no canto INFERIOR-DIREITO")
            elif len(clicks) == 2:
                self.root.after(0, lambda: (self.root.deiconify(),
                                            on_done(clicks)))
                return False  # stop listener

        listener = pynput_mouse.Listener(on_click=on_click)
        listener.start()

    def _finish_battle_list_calibration(self, clicks):
        (x1, y1), (x2, y2) = clicks
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        self.cfg["battle_list"] = {"x": x, "y": y, "width": w, "height": h}
        save_config(self.cfg)
        self.log(f"battle list calibrada: x={x} y={y} w={w} h={h}")
        self._refresh()
```

- [ ] **Step 2: Testar manualmente**

Run: `python ui.py`
1. Clicar "Calibrar battle list"
2. Janela some, clicar canto superior-esquerdo da battle list no Tibia
3. Clicar canto inferior-direito
4. Janela volta; label atualizada com coordenadas

Expected: label "Battle list: x=... y=... w=... h=..." aparece.

- [ ] **Step 3: Commit**

```bash
git add ui.py
git commit -m "feat: calibrate battle list region via two clicks"
```

---

### Task 9: UI — adicionar markers por clique

**Files:**
- Modify: `ui.py`

- [ ] **Step 1: Substituir `_add_marker` em `ui.py`**

Localizar `_add_marker` e substituir por:

```python
    def _add_marker(self):
        self.log("adicione marker: clique na posição da tela")
        self.root.withdraw()

        def on_click(x, y, button, pressed):
            if not pressed:
                return
            self.root.after(0, lambda: self._finish_add_marker(x, y))
            return False

        listener = pynput_mouse.Listener(on_click=on_click)
        listener.start()

    def _finish_add_marker(self, x, y):
        self.root.deiconify()
        self.cfg.setdefault("markers", []).append({"x": x, "y": y})
        save_config(self.cfg)
        self.log(f"marker adicionado: ({x}, {y})")
        self._refresh()
```

- [ ] **Step 2: Testar manualmente**

Run: `python ui.py`
1. Clicar "Adicionar marker"
2. Clicar em algum lugar da tela
3. Marker deve aparecer na lista
4. Repetir 3+ vezes
5. "Remover selecionado" → remove
6. "Limpar todos" → esvazia

Expected: lista reflete operações; `config.json` é atualizado.

- [ ] **Step 3: Commit**

```bash
git add ui.py
git commit -m "feat: add markers via click-capture"
```

---

### Task 10: Teste integrado manual (golden path)

**Files:**
- nenhum (teste manual de ponta-a-ponta)

- [ ] **Step 1: Preparar Tibia**

- Abra o Tibia em local seguro (ex: área com monstros fracos como Infernoid)
- Mantenha a battle list visível no canto direito
- Garanta que a tecla de ataque padrão é espaço e que option+Q é o atalho de loot nas configurações do Tibia.

- [ ] **Step 2: Calibrar e configurar**

Run: `cd /Users/gustavonavarro/tibia-bot && source .venv/bin/activate && python ui.py`

1. Calibrar battle list (cobrir toda a área onde aparecem inimigos)
2. Adicionar 3-5 markers em posições distintas do minimap (onde quer que o personagem ande)
3. Ajustar walk delay min/max se necessário
4. Clicar "Iniciar"

- [ ] **Step 3: Observar comportamentos esperados**

Verificar no log:
- [ ] Com battle list vazia e markers: bot clica markers aleatoriamente
- [ ] Quando monstro aparece na battle list: log mostra "space"
- [ ] Enquanto atacando (quadrado vermelho visível): sem novos "space", sem "click"
- [ ] Após matar: log mostra "loot (alt+q)"
- [ ] Depois retoma andando pelos markers

- [ ] **Step 4: Ajustes finos (se necessário)**

Se `has_target_in_battle_list` for falso positivo/negativo, ajustar `GREEN_HP_MIN_PIXELS` em `detection.py`. Se `is_attacking` for errático, ajustar `RED_ATTACK_MIN_PIXELS`. Commitar ajustes:

```bash
git add detection.py
git commit -m "tune: adjust detection thresholds from field testing"
```

- [ ] **Step 5: Commit final**

Se tudo funcionou e nada mais mudou:

```bash
git status
# se houver config.json novo gerado pela UI, decidir se commitar ou não
```

---

## Self-Review Check

- **Spec coverage:**
  - Apagar tudo → Task 1 ✓
  - UI pra configuração → Tasks 7, 8, 9 ✓
  - Andar por markers aleatórios → Tasks 6 (state machine) + 9 (UI) ✓
  - Espaço quando alvo na battle list → Task 4 (detecção) + Task 6 (ação) ✓
  - Esperar matar (quadrado vermelho) → Task 4 (`is_attacking`) + Task 6 ✓
  - option+Q loot após kill → Task 5 (`loot_alt_q`) + Task 6 (transição was_attacking → not attacking) ✓

- **Placeholders:** nenhum TBD/TODO remanescente em código; os `messagebox.showinfo("TODO", ...)` na Task 7 são explicitamente substituídos nas Tasks 8 e 9.

- **Type consistency:** `Bot.__init__` parâmetros (`is_attacking`, `has_target`, `press_space`, `loot`, `click`, `sleep`, `choose_marker`, `walk_delay`, `get_markers`) batem com os usados em `BotRunner._loop` e com `make_bot` nos testes. Chaves de config (`battle_list`, `markers`, `walk_delay_min`, `walk_delay_max`) batem entre `default_config`, `detection`/`capture` call sites e UI.
