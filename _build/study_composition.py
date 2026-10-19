# -*- coding: utf-8 -*-
"""Composition statistics of the reference film, sampled every N frames."""
import os, sys, json
import numpy as np
import cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMPROOT = os.environ.get("TMP", os.path.join(ROOT, "_tmp"))

SRC = os.path.join(ROOT, "过期童话.mp4")
HERE = os.path.dirname(os.path.abspath(__file__))
cap = cv2.VideoCapture(SRC)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
STEP = max(1, n // 240)

rows = []
i = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    if i % STEP:
        i += 1
        continue
    g = cv2.cvtColor(cv2.resize(fr, (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
    H, W = g.shape
    m, s = g.mean(), g.std()
    ink = (g > m + 1.2 * s).astype(np.float32)        # bright matter (subject + type)
    dark = (g < m - 0.6 * s).astype(np.float32)       # negative space
    ys, xs = np.nonzero(ink > 0.5)
    if len(xs) < 60:
        i += 1
        continue
    cx, cy = xs.mean() / W, ys.mean() / H
    bw = (xs.max() - xs.min()) / W
    bh = (ys.max() - ys.min()) / H
    # third-of-frame occupancy of ink
    thirds = [ink[:, :W // 3].mean(), ink[:, W // 3:2 * W // 3].mean(), ink[:, 2 * W // 3:].mean()]
    rows.append(dict(t=i / 24.0, cx=round(float(cx), 3), cy=round(float(cy), 3),
                     bw=round(float(bw), 3), bh=round(float(bh), 3),
                     ink=round(float(ink.mean()) * 100, 2), dark=round(float(dark.mean()) * 100, 1),
                     thirds=[round(float(x) * 100, 2) for x in thirds],
                     lum=round(float(m), 1)))
    i += 1
cap.release()

cx = np.array([r["cx"] for r in rows])
bw = np.array([r["bw"] for r in rows])
bh = np.array([r["bh"] for r in rows])
ink = np.array([r["ink"] for r in rows])
dark = np.array([r["dark"] for r in rows])

print("samples", len(rows))
print("subject x centroid: mean %.2f  median %.2f  |left(<.4) %.0f%%  center %.0f%%  right(>.6) %.0f%%" % (
    cx.mean(), np.median(cx), (cx < 0.4).mean() * 100, ((cx >= 0.4) & (cx <= 0.6)).mean() * 100, (cx > 0.6).mean() * 100))
print("bright bbox width  mean %.2f   height mean %.2f" % (bw.mean(), bh.mean()))
print("ink coverage %%: mean %.2f  p90 %.2f" % (ink.mean(), np.percentile(ink, 90)))
print("dark coverage %%: mean %.1f" % dark.mean())
h, edges = np.histogram(bw, bins=[0, .3, .5, .7, .9, 1.01])
print("bbox width histogram:", dict(zip(["<.3", ".3-.5", ".5-.7", ".7-.9", ">.9"], h.tolist())))
json.dump(rows, open(os.path.join(HERE, "motion", "composition.json"), "w"), indent=0)
print("wrote motion/composition.json")
