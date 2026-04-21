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
