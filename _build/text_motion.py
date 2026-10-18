# -*- coding: utf-8 -*-
"""Track how TEXT behaves frame by frame: onset order, scale, drift, orientation.

usage: python text_motion.py <video> <t0> <t1> [step]
Writes: masks/<tag>_%03d.png (binary text masks) + a printed trajectory table.
"""
import os
import sys
import numpy as np
import cv2

SRC = sys.argv[1]
T0 = float(sys.argv[2])
T1 = float(sys.argv[3])
STEP = int(sys.argv[4]) if len(sys.argv) > 4 else 2
TAG = "w%d" % int(T0)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "masks")
os.makedirs(OUT, exist_ok=True)

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
cap.set(cv2.CAP_PROP_POS_FRAMES, int(T0 * fps))
n = int(round((T1 - T0) * fps))
print("%-7s %-9s %-9s %-8s %-8s %-7s %-7s %s" %
      ("t", "area%", "cx", "cy", "w", "h", "angle", "cols"))
prev = None
rows = []
for k in range(0, n, STEP):
    ok, fr = cap.read()
    if not ok:
        break
    if k and STEP > 1:
        for _ in range(STEP - 1):
            cap.read()
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    m, s = g.mean(), g.std()
    mask = ((g > m + 1.55 * s) & (g > 120)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    area = float((mask > 0).mean() * 100)
    ys, xs = np.nonzero(mask)
    if len(xs) < 200:
        print("%-7.2f %-9s" % (T0 + k / fps, "—"))
        continue
    cx, cy = xs.mean(), ys.mean()
    w = xs.max() - xs.min()
    h = ys.max() - ys.min()
    # principal orientation of the ink cloud
    X = np.stack([xs - cx, ys - cy]).astype(np.float32)
    cov = X @ X.T / len(xs)
    evals, evecs = np.linalg.eigh(cov)
    ang = float(np.degrees(np.arctan2(evecs[1, -1], evecs[0, -1])))
    # column profile -> how many separate vertical text columns exist
    colsum = mask.sum(axis=0)
    on = colsum > colsum.max() * 0.18
    cols = int(np.sum(np.diff(np.r_[0, on.astype(int), 0]) == 1))
    rows.append((T0 + k / fps, area, cx, cy, w, h, ang, cols))
    print("%-7.2f %-9.2f %-9.1f %-8.1f %-8d %-7d %-7.1f %d" %
          (T0 + k / fps, area, cx, cy, w, h, ang, cols))
    if (k // STEP) % 2 == 0:
        cv2.imwrite(os.path.join(OUT, "%s_%03d.png" % (TAG, k)), mask)
cap.release()

if len(rows) > 3:
    a = np.array([r[1] for r in rows])
    cx = np.array([r[2] for r in rows])
    an = np.array([r[6] for r in rows])
    print("\narea: first %.2f  max %.2f  last %.2f  (growth x%.1f)" % (a[0], a.max(), a[-1], a.max() / max(0.1, a[0])))
    print("centroid drift: dx %.1f px, dy %.1f px over %.1f s" % (cx[-1] - cx[0], 0, (rows[-1][0] - rows[0][0])))
    print("orientation range: %.1f .. %.1f deg" % (an.min(), an.max()))
