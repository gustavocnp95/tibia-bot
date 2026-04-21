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
