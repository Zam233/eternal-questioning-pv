# -*- coding: utf-8 -*-
"""Count text events per shot in the reference film.

For every frame: bright-ink mask area + bounding extents. Then, inside each shot
(from motion/report.json), count discontinuities = moments where the text layer
visibly changes (new line lands / old line clears).
"""
import json
import os, sys
import numpy as np
import cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMPROOT = os.environ.get("TMP", os.path.join(ROOT, "_tmp"))

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "过期童话.mp4")
rep = json.load(open(os.path.join(HERE, "motion", "report.json")))
cuts = [0] + rep["cut_frames"] + [rep["frames"] - 1]

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
areas, ex, ey = [], [], []
i = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    g = cv2.cvtColor(cv2.resize(fr, (426, 240), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
    m, s = g.mean(), g.std()
    mask = ((g > m + 1.5 * s) & (g > 120)).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    areas.append(float(mask.mean()))
    ys, xs = np.nonzero(mask)
    ex.append((xs.min(), xs.max()) if len(xs) > 300 else (0, 0))
    ey.append((ys.min(), ys.max()) if len(ys) > 300 else (0, 0))
    i += 1
cap.release()
A = np.array(areas)
print("frames", len(A))

events_per_shot = []
shot_rows = []
for k in range(len(cuts) - 1):
    a, b = cuts[k], cuts[k + 1]
    if b - a < 12:
        continue
    seg = A[a:b]
    if seg.max() < 0.004:
        shot_rows.append((a / fps, (b - a) / fps, 0, "no text"))
        continue
    # events: relative jumps in bright-ink area
    ev = 0
    j = 2
    while j < len(seg) - 2:
        prev = seg[max(0, j - 3):j].mean()
        nxt = seg[j:j + 3].mean()
        if abs(nxt - prev) > max(0.004, 0.35 * max(prev, nxt)) and j > 6:
            ev += 1
            j += 8
        else:
            j += 1
    events_per_shot.append(ev)
    dur = (b - a) / fps
    shot_rows.append((a / fps, dur, ev, "%.2f ev/s" % (ev / max(0.3, dur))))

ev = np.array(events_per_shot)
print("shots with text:", len(ev))
print("text events per shot: median %.0f  mean %.1f  max %d" % (np.median(ev), ev.mean(), ev.max()))
print("text events per second: %.2f" % (ev.sum() / 284.16))
longs = [r for r in shot_rows if r[1] > 3.5]
print("long shots (>3.5 s): %d, mean events %.1f" % (len(longs), np.mean([r[2] for r in longs]) if longs else 0))

with open(os.path.join(HERE, "motion", "text_events.txt"), "w", encoding="utf-8") as f:
    f.write("t0      dur     events\n")
    for r in shot_rows:
        f.write("%-8.2f %-7.2f %-6d %s\n" % r)
json.dump(dict(median=float(np.median(ev)), mean=float(ev.mean()), max=int(ev.max()),
               total=int(ev.sum()), rows=[[float(x) for x in r[:3]] for r in shot_rows]),
          open(os.path.join(HERE, "motion", "text_events.json"), "w"), indent=1)
print("wrote motion/text_events.txt")
