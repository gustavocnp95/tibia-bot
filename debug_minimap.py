"""Captura o minimap via mss (exatamente como o bot faz) e dumpa:
1. PNG da captura em debug_out/live_minimap.png (na pasta do projeto)
2. Histograma dos pixels "verdosos"
3. Blobs conectados + suas cores predominantes

Saída vai pra stdout E pra debug_out/report.txt.
Uso: python3 debug_minimap.py
"""
import json
import os
import sys
from collections import Counter
import numpy as np
from PIL import Image
import capture


OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_out")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    report_path = os.path.join(OUT_DIR, "report.txt")
    log_file = open(report_path, "w")

    def log(msg=""):
        print(msg)
        log_file.write(str(msg) + "\n")

    with open("config.json") as f:
        cfg = json.load(f)
    region = cfg["minimap"]
    bgra = capture.grab_region(region)
    log(f"capture shape: {bgra.shape}  region: {region}")

    png_path = os.path.join(OUT_DIR, "live_minimap.png")
    Image.fromarray(bgra[:, :, [2, 1, 0]]).save(png_path)
    log(f"saved {png_path}")

    b, g, r = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2]

    # greenish: G dominant
    m = (g.astype(np.int16) > r.astype(np.int16) + 15) & \
        (g.astype(np.int16) > b.astype(np.int16) + 15) & (g > 80)
    log(f"\ngreen-dominant pixels: {int(m.sum())}")

    # top color buckets
    buckets = Counter()
    for R, G, B in zip(r[m]//10*10, g[m]//10*10, b[m]//10*10):
        buckets[(int(R), int(G), int(B))] += 1
    log("top 20 green buckets (R,G,B)/10*10 -> count:")
    for (R, G, B), c in buckets.most_common(20):
        log(f"  ({R:3d},{G:3d},{B:3d}): {c}")

    # connected blobs
    H, W = m.shape
    visited = np.zeros_like(m, dtype=bool)
    blobs = []
    for y in range(H):
        for x in range(W):
            if not m[y, x] or visited[y, x]:
                continue
            stack = [(x, y)]
            visited[y, x] = True
            pts = []
            while stack:
                cx, cy = stack.pop()
                pts.append((cx, cy))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and m[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((nx, ny))
            if len(pts) >= 3:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                cen = (sum(xs)//len(pts), sum(ys)//len(pts))
                bb = (min(xs), min(ys), max(xs), max(ys))
                # color avg
                avg_r = int(np.mean([r[py, px] for px, py in pts]))
                avg_g = int(np.mean([g[py, px] for px, py in pts]))
                avg_b = int(np.mean([b[py, px] for px, py in pts]))
                blobs.append((len(pts), cen, bb, (avg_r, avg_g, avg_b)))

    blobs.sort(reverse=True)
    log(f"\n{len(blobs)} blobs (>=3 px):")
    for sz, cen, bb, rgb in blobs[:15]:
        w = bb[2]-bb[0]+1
        h = bb[3]-bb[1]+1
        log(f"  size={sz:3d}  cen={cen}  bbox={w}x{h}  avgRGB={rgb}")

    log_file.close()
    print(f"\nreport saved to {report_path}")


if __name__ == "__main__":
    main()
