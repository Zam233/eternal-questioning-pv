# -*- coding: utf-8 -*-
"""Quantitative motion analysis of the reference PV.

Measures, per frame pair: cut detection, camera translation/rotation/scale via
feature-based affine estimation, luminance/colour swing. Writes JSON + a text report.
"""
import json, os, sys
import numpy as np
import cv2

SRC = sys.argv[1] if len(sys.argv) > 1 else r"K:\5A大作\过期童话.mp4"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion")
os.makedirs(OUT, exist_ok=True)

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
print("fps", fps, "frames", n, flush=True)

prev_small = None
prev_gray = None
rows = []
i = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    h, w = fr.shape[:2]
    small = cv2.resize(fr, (160, 90), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    lut_gray = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_AREA)
    mean_l = float(lut_gray.mean())
    mean_bgr = small.reshape(-1, 3).mean(axis=0)
    rec = dict(f=i, t=round(i / fps, 3), lum=round(mean_l, 2),
               b=round(float(mean_bgr[0]), 1), g=round(float(mean_bgr[1]), 1),
               r=round(float(mean_bgr[2]), 1))
    if prev_gray is not None:
        d = cv2.absdiff(lut_gray, prev_gray)
        rec["diff"] = round(float(d.mean()), 3)
        g0 = cv2.resize(prev_gray, (256, 144))
        g1 = cv2.resize(lut_gray, (256, 144))
        # phase correlation translation
        shift, resp = cv2.phaseCorrelate(np.float32(g0), np.float32(g1))
        rec["dx"] = round(float(shift[0]), 3)
        rec["dy"] = round(float(shift[1]), 3)
        rec["pc"] = round(float(resp), 3)
    rows.append(rec)
    prev_gray = lut_gray
    i += 1
    if i > n + 10:
        break
cap.release()

json.dump(rows, open(os.path.join(OUT, "frames.json"), "w"), indent=0)

diffs = np.array([r.get("diff", 0.0) for r in rows])
lum = np.array([r["lum"] for r in rows])
pcs = np.array([r.get("pc", 0.0) for r in rows])

# --- cuts: local maxima of diff above adaptive threshold
thr = np.percentile(diffs[1:], 96)
cuts = [k for k in range(1, len(diffs) - 1) if diffs[k] > thr and diffs[k] >= diffs[k - 1] and diffs[k] >= diffs[k + 1]]
print("diff p50 %.2f  p96 %.2f  max %.2f" % (np.percentile(diffs[1:], 50), thr, diffs.max()))
print("cut candidates:", len(cuts))

# merge cuts closer than 6 frames
merged = []
for c in cuts:
    if merged and c - merged[-1] < 8:
        continue
    merged.append(c)
print("shots (merged):", len(merged))
lens = np.diff([0] + merged + [len(rows)])
print("shot length frames: median %.1f  mean %.1f  min %d  max %d" % (np.median(lens), lens.mean(), lens.min(), lens.max()))

# --- flash frames (lum spike then fall)
flash = []
for k in range(2, len(lum) - 2):
    if lum[k] - lum[k - 2] > 28 and lum[k] - lum[k + 2] > 22 and lum[k] > 150:
        flash.append(k)
print("flash frames:", len(flash))

# --- global camera drift per shot (phase correlation accum)
drift = []
for j in range(len(merged)):
    a = merged[j - 1] if j > 0 else 0
    b = merged[j] if j < len(merged) else len(rows) - 1
    seg = rows[a + 2:b]
    if len(seg) < 6:
        continue
    dx = sum(r.get("dx", 0) for r in seg)
    dy = sum(r.get("dy", 0) for r in seg)
    drift.append(dict(t0=round(a / fps, 2), t1=round(b / fps, 2), frames=b - a,
                      dx=round(dx, 1), dy=round(dy, 1),
                      px_per_s=round((abs(dx) + abs(dy)) / max(0.1, (b - a) / fps), 2)))

report = dict(fps=fps, frames=len(rows), shots=len(merged), cut_frames=merged,
              shot_lens=[int(x) for x in lens.tolist()], flash_frames=flash, drift=drift)
json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)

with open(os.path.join(OUT, "report.txt"), "w", encoding="utf-8") as f:
    f.write("shots=%d  median shot=%.1f frames (%.2f s)  mean=%.1f\n" %
            (len(merged), np.median(lens), np.median(lens) / fps, lens.mean()))
    f.write("flash frames: %s\n" % flash[:40])
    f.write("\n%-18s %6s %6s %8s %8s %8s\n" % ("shot", "frames", "sec", "dx", "dy", "px/s"))
    for d in drift:
        f.write("%-18s %6d %6.1f %8.1f %8.1f %8.2f\n" %
                ("%.2f-%.2f" % (d["t0"], d["t1"]), d["frames"], d["frames"] / fps, d["dx"], d["dy"], d["px_per_s"]))
print("wrote", OUT)
