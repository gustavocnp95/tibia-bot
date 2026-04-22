"""UI tkinter para configurar e controlar o bot."""
import os
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
from PIL import Image
from pynput import mouse as pynput_mouse

import capture
import detection
from config import load_config, save_config
from bot import BotRunner


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Tibia Bot")
        self.root.geometry("520x520")
        self.cfg = load_config()
        self.runner = BotRunner(cfg_provider=lambda: self.cfg, log_fn=self.log)

        self._build_ui()
        self._refresh()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        regions_frame = ttk.LabelFrame(self.root, text="Regiões (calibrar com 2 cliques)")
        regions_frame.pack(fill="x", **pad)

        self.battle_list_label = ttk.Label(regions_frame, text="Battle list: -")
        self.battle_list_label.pack(anchor="w", padx=6)
        ttk.Button(regions_frame, text="Calibrar battle list",
                   command=self._calibrate_battle_list).pack(anchor="w", padx=6, pady=2)

        self.minimap_label = ttk.Label(regions_frame, text="Minimap: -")
        self.minimap_label.pack(anchor="w", padx=6, pady=(8, 0))
        ttk.Button(regions_frame, text="Calibrar minimap",
                   command=self._calibrate_minimap).pack(anchor="w", padx=6, pady=2)

        delay_frame = ttk.LabelFrame(self.root, text="Walk delay (segundos)")
        delay_frame.pack(fill="x", **pad)
        self.delay_min_var = tk.DoubleVar(value=self.cfg["walk_delay_min"])
        self.delay_max_var = tk.DoubleVar(value=self.cfg["walk_delay_max"])
        ttk.Label(delay_frame, text="Min:").grid(row=0, column=0, padx=4, pady=2)
        ttk.Entry(delay_frame, textvariable=self.delay_min_var, width=8).grid(row=0, column=1)
        ttk.Label(delay_frame, text="Max:").grid(row=0, column=2, padx=4)
        ttk.Entry(delay_frame, textvariable=self.delay_max_var, width=8).grid(row=0, column=3)
        ttk.Button(delay_frame, text="Salvar", command=self._save_delays).grid(row=0, column=4, padx=6)

        ctrl = ttk.Frame(self.root)
        ctrl.pack(fill="x", **pad)
        self.start_btn = ttk.Button(ctrl, text="Iniciar", command=self._start)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ttk.Button(ctrl, text="Parar", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        ttk.Button(ctrl, text="Debug snapshot", command=self._debug_snapshot).pack(side="left", padx=6)

        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=14, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=4)

    def _refresh(self):
        self.battle_list_label.config(text=_fmt_region("Battle list", self.cfg.get("battle_list")))
        self.minimap_label.config(text=_fmt_region("Minimap", self.cfg.get("minimap")))

    def log(self, msg):
        self.root.after(0, self._append_log, str(msg))

    def _append_log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _calibrate_battle_list(self):
        self.log("calibrando battle list: clique no canto SUPERIOR-ESQUERDO")
        self.root.withdraw()
        self._capture_two_clicks(self._finish_calibration("battle_list"))

    def _calibrate_minimap(self):
        self.log("calibrando minimap: clique no canto SUPERIOR-ESQUERDO")
        self.root.withdraw()
        self._capture_two_clicks(self._finish_calibration("minimap"))

    def _capture_two_clicks(self, on_done):
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
                return False

        listener = pynput_mouse.Listener(on_click=on_click)
        listener.start()

    def _finish_calibration(self, cfg_key):
        def done(clicks):
            (x1, y1), (x2, y2) = clicks
            region = {
                "x": min(x1, x2),
                "y": min(y1, y2),
                "width": abs(x2 - x1),
                "height": abs(y2 - y1),
            }
            self.cfg[cfg_key] = region
            save_config(self.cfg)
            self.log(f"{cfg_key} calibrada: {region}")
            self._refresh()
        return done

    def _save_delays(self):
        self.cfg["walk_delay_min"] = float(self.delay_min_var.get())
        self.cfg["walk_delay_max"] = float(self.delay_max_var.get())
        save_config(self.cfg)
        self.log("delays salvos")

    def _start(self):
        if not self.cfg.get("battle_list"):
            messagebox.showerror("Erro", "Calibre a battle list primeiro.")
            return
        if not self.cfg.get("minimap"):
            messagebox.showerror("Erro", "Calibre o minimap primeiro.")
            return
        self.runner.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def _stop(self):
        self.runner.stop()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _debug_snapshot(self):
        out_dir = os.path.join(os.getcwd(), "debug")
        os.makedirs(out_dir, exist_ok=True)
        self._snapshot_region("battle_list", out_dir)
        self._snapshot_region("minimap", out_dir)

    def _snapshot_region(self, key, out_dir):
        region = self.cfg.get(key)
        if not region:
            self.log(f"{key}: não calibrada")
            return
        img = capture.grab_region(region)
        if img is None:
            self.log(f"{key}: captura retornou None")
            return
        path = os.path.join(out_dir, f"{key}.png")
        rgb = img[:, :, [2, 1, 0]]
        Image.fromarray(rgb.astype(np.uint8)).save(path)
        green_count = int(detection._green_hp_mask(img).sum())
        red_count = int(detection._red_attack_mask(img).sum())
        neon_count = int(detection._green_check_mask(img).sum())
        markers = detection.find_green_check_markers(img)
        self.log(f"{key} salvo em {path}")
        self.log(f"  pixels HP-green={green_count}  attack-red={red_count}  "
                 f"neon-green={neon_count}  markers={len(markers)}")
        if key == "battle_list":
            self.log(f"  has_target={detection.has_target_in_battle_list(img)}  "
                     f"is_attacking={detection.is_attacking(img)}")


def _fmt_region(label, region):
    if not region:
        return f"{label}: (não calibrada)"
    return (f"{label}: x={region['x']:.0f} y={region['y']:.0f} "
            f"w={region['width']:.0f} h={region['height']:.0f}")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
