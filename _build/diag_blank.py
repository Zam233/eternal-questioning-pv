# -*- coding: utf-8 -*-
"""看看被判空带的那些块到底有多"死"（含邻块对比）。"""
import os
import subprocess
import numpy as np
from PIL import Image

SRC = r"K:\5A大作\out\永恒追问_PV_1080p.mp4"
TMP = r"K:\dsh_tmp\diag_blank"
os.makedirs(TMP, exist_ok=True)
CASES = [(56.88, 0, 8), (111.58, 1, 23), (111.75, 1, 23), (123.42, 0, 1)]

for t, axis, blk in CASES:
    p = os.path.join(TMP, "t%.2f.png" % t)
    if not os.path.exists(p):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % t, "-i", SRC,
                        "-frames:v", "1", p], check=True)
    g = np.asarray(Image.open(p).convert("L"), np.float32)
    H, W = g.shape
    n = 24
    step = (W if axis == 0 else H) // n
    lo = blk * step
    hi = min((blk + 1) * step, W if axis == 0 else H)
    sl = g[:, lo:hi] if axis == 0 else g[lo:hi, :]
    nb = []
    for k in (blk - 1, blk + 1):
        if 0 <= k < n:
            a, b = k * step, min((k + 1) * step, W if axis == 0 else H)
            s2 = g[:, a:b] if axis == 0 else g[a:b, :]
            nb.append((k, round(float(s2.mean()), 1), round(float(s2.std()), 2)))
    print("t=%.2f axis=%s blk=%d  mean=%.1f std=%.2f   neigbours=%s"
          % (t, "横" if axis == 0 else "纵", blk, sl.mean(), sl.std(), nb))
