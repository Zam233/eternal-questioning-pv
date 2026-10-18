# -*- coding: utf-8 -*-
"""v8 opening: ONE continuous camera, ten tableaux dissolving into each other.

Following the reference's 00:02-00:32: no cuts, a single travelling camera, the
images cross-dissolve, and one constant line of type anchors the whole run.
"""
import json, io, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ERA = [
    ("era01_ionia", "古希腊早期哲学", "前 6 世纪 · 水与火"),
    ("era02_cave_academy", "古希腊古典哲学", "前 4 世纪 · 洞穴与理念"),
    ("era03_gothic", "中古哲学", "5–15 世纪 · 信仰与理性"),
    ("era04_slate_mirror", "经验论与唯理论", "17–18 世纪 · 白板与天赋"),
    ("era05_bastille", "法国大革命", "1789 · 自由与平等"),
    ("era06_factory_book", "马克思主义", "1848 · 资本与劳动"),
    ("era07_winterpalace", "十月革命", "1917 · 实践与革命"),
    ("era08_lab", "实用主义", "19 世纪 · 有用即真"),
    ("era09_logic_board", "分析哲学", "20 世纪 · 语言与逻辑"),
    ("era10_machine", "人工智能哲学", "21 世纪 · 心智与机器"),
]
X = 0.60          # crossfade seconds
CARD = 2.40       # each tableau lives this long
TOTAL = 18.90

ASH = dict(key=(226, 214, 196), amount=0.26, contrast=1.03, lift=0.004)
RED = dict(key=(220, 96, 72), amount=0.42, contrast=1.08, lift=-0.012)
shots = []
for i, (key, name, sub) in enumerate(ERA):
    a = round(i * (CARD - X), 3)
    b = round(a + CARD, 3)
    if b > TOTAL:
        b = TOTAL
    # one continuous camera: keep accelerating forward, drift left, roll a hair
    z0 = 0.012 + i * 0.010
    z1 = z0 + 0.085
    cam = dict(seed=20 + i, handheld=1.1, aperture=1.4, max_blur=5,
               keys=[(0.0, -0.010 + 0.002 * i, 0.004, z0, -0.18 + 0.03 * i, 0.62),
                     (0.45, 0.000, 0.000, (z0 + z1) / 2, 0.0, 0.62),
                     (1.0, 0.012, -0.004, z1, 0.16 - 0.03 * i, 0.62)])
    layers = [
        dict(t="bg", src=key, idx=0, z=1.00, palette="sepia", fit=1.06),
        dict(t="fx", mode="dust", z=0.55, count=60 + i * 5, alpha=0.36, speed=0.026, seed=60 + i),
        dict(t="type", z=0.30, cue=dict(kind="band", text=name, t0=a + 0.35, t1=b - 0.15,
                                        layout="center", px=132, justify=True, band=0.72,
                                        dy=0.10, erase=True, words=[], glow=0.45, seed=100 + i)),
        dict(t="type", z=0.30, cue=dict(kind="note", text=sub, t0=a + 0.50, t1=b - 0.10,
                                        layout="center", px=30, alpha=0.85, dy=0.26, raw_text=True,
                                        words=[], glow=0.0, seed=200 + i)),
    ]
    if i in (1, 4, 8):
        layers.insert(2, dict(t="map", src="map_ancient" if i == 1 else "map_voyage",
                              z=0.44, x=0.26, y=0.62, w=0.34, rot=-7, rot_speed=1.8,
                              alpha=0.40, u_in=0.20))
    if i == 4:      # 法国大革命：三色旗从暗里显影
        layers.insert(2, dict(t="prop", src="flag_fr", z=0.34, x=0.74, y=0.52, h=0.78,
                              tilt=-7, alpha=0.55))
    if i in (5, 6):  # 马克思主义 / 十月革命：红旗压得很低
        layers.insert(2, dict(t="prop", src="flag_red", z=0.36, x=0.80, y=0.48, h=0.86,
                              tilt=6, alpha=0.45))
    shots.append(dict(t0=a, t1=b, xfade=X, seed=100 + i, palette="sepia",
                      glitch=[0.03, 0.07], grade=(RED if i in (4, 5, 6) else ASH), cam=cam,
                      caption=None, anno=None, layers=layers))

json.dump(shots, open(os.path.join(HERE, "shots_v8_open.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("opening shots", len(shots), "total", shots[-1]["t1"], "s, xfade", X)


