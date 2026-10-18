# -*- coding: utf-8 -*-
"""Scan the rendered sample for empty bands: a blank strip left where two
scenes meet shows up as a column/row block with almost no variance."""
import json, io, os, subprocess, sys
from PIL import Image
import numpy as np

SRC = r"K:\5A大作\out\v14_open8.mp4"
TMP = r"K:\dsh_tmp\scan_blank"
os.makedirs(TMP, exist_ok=True)
shots = json.load(io.open(r"K:\5A大作\_build\shots_v13.json", encoding="utf-8"))
shots.sort(key=lambda s: s["t0"])

wins = [(s["t0"], s["t0"] + (s.get("link") or {}).get("dur", 0), (s.get("link") or {}).get("out"))
        for s in shots if s.get("link")]

bad = []
for t0, t1, out in wins:
    a = max(0.0, t0 - 0.25)
    b = t1 + 0.25
    fa, fb = int(a * 24), int(b * 24)
    for f in range(fa, fb):
        t = f / 24.0
        p = os.path.join(TMP, "f%05d.png" % f)
        if not os.path.exists(p):
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.4f" % (f / 24.0),
                            "-i", SRC, "-frames:v", "1", p], check=True)
        im = Image.open(p).convert("L")
        g = np.asarray(im, np.float32)
        H, W = g.shape
        # horizontal blocks (would reveal a vertical blank strip) and vertical blocks
        for axis in (0, 1):
            n = 24
            m = W if axis == 0 else H
            step = m // n
            for i in range(n):
                sl = g[:, i * step:(i + 1) * step] if axis == 0 else g[i * step:(i + 1) * step, :]
                if sl.std() < 1.6 and sl.mean() < 26:
                    bad.append((round(t, 2), out, axis, i, round(float(sl.mean()), 1),
                                round(float(sl.std()), 2)))
                    break
print("windows:", len(wins))
if not bad:
    print("OK: no flat/empty band found around any hand-over")
else:
    for b in bad[:40]:
        print("  t=%.2f out=%-5s axis=%d block=%d mean=%.1f std=%.2f" % b)
    print("total", len(bad))
