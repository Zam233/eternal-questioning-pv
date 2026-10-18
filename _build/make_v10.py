# -*- coding: utf-8 -*-
"""v10: opening (10 dissolving tableaux) + scenes 1-8 with material-driven transitions.

Transition is chosen by the material, per the frame study:
  same space        -> PUSH / TRUCK / RISE  (camera carries)
  leaving a face    -> BURN                 (blows out to white, next develops)
  light/dark match  -> CUT                  (no overlap at all)
  emotional turn    -> FLASH (black / warm / cold)
  same-subject rush -> WHIP
"""
import json, io, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PUNCT = re.compile(r'[\s\u3000"\u201c\u201d\'\u2018\u2019,，.。!！?？;；:：、]')

rows = json.load(io.open(os.path.join(HERE, "timing_auto.json"), encoding="utf-8"))
BY = {PUNCT.sub("", r["text"]): r for r in rows}

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
WARM = dict(key=(255, 152, 96), amount=0.34, contrast=1.07, lift=-0.012)
COLD = dict(key=(188, 210, 238), amount=0.30, contrast=1.06, lift=0.0)
GOLD = dict(key=(238, 196, 128), amount=0.30, contrast=1.04, lift=0.008)
ASH = dict(key=(226, 214, 196), amount=0.26, contrast=1.03, lift=0.004)
RED = dict(key=(220, 96, 72), amount=0.42, contrast=1.08, lift=-0.012)

shots = []

# ---------------------------------------------------------------- opening
X = 0.60
CARD = 2.40
for i, (key, name, sub) in enumerate(ERA):
    a = round(i * (CARD - X), 3)
    b = round(min(a + CARD, 18.90), 3)
    z0 = 0.012 + i * 0.010
    z1 = z0 + 0.085
    cam = dict(seed=20 + i, handheld=1.1, aperture=1.4, max_blur=5,
               keys=[(0.0, -0.010 + 0.002 * i, 0.004, z0, -0.18 + 0.03 * i, 0.62),
                     (0.45, 0.000, 0.000, (z0 + z1) / 2 * 1.05, 0.0, 0.62),
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
    if i == 4:
        layers.insert(2, dict(t="prop", src="flag_fr", z=0.34, x=0.74, y=0.52, h=0.78,
                              tilt=-7, alpha=0.55))
    if i in (5, 6):
        layers.insert(2, dict(t="prop", src="flag_red", z=0.36, x=0.80, y=0.48, h=0.86,
                              tilt=6, alpha=0.45))
    shots.append(dict(t0=a, t1=b, xfade=X, seed=100 + i, palette="sepia",
                      glitch=[0.03, 0.07], grade=(RED if i in (4, 5, 6) else ASH), cam=cam,
                      trans_in=("flash_warm" if i == 1 else None),
                      caption=None, anno=None, layers=layers))

# ---------------------------------------------------------------- scenes 1-8
def cue(text, kind="band", layout=None, px=None, **kw):
    key = PUNCT.sub("", text)
    r = BY.get(key)
    t0 = kw.pop("t0", None); t1 = kw.pop("t1", None)
    if r is None:
        base = dict(t0=t0, t1=t1 if t1 is not None else t0 + 3.0); words = []
    else:
        base = dict(t0=r["t0"], t1=r["t1"] + 0.30)
        words = [{"w": w["t0"]} for w in r["words"]]
        words = [{"t0": w["w"]} for w in words]
    c = dict(kind=kind, text=key, t0=base["t0"], t1=base["t1"],
             layout=layout or "center", px=px, words=words, glow=0.45,
             seed=abs(hash(key)) % 9999)
    c.update(kw)
    return c


def TY(c, z=0.30):
    return dict(t="type", z=z, cue=c)


def build(t0, palette, grade, layers, cam, cap, anno, seed,
          trans=None, xfade=0.55, glitch=(0.04, 0.12)):
    cues = [L["cue"] for L in layers if L.get("t") == "type"]
    cues.sort(key=lambda c: c["t0"])
    for i in range(len(cues) - 1):
        cues[i]["t1"] = min(cues[i]["t1"], cues[i + 1]["t0"] - 0.12)
    t1 = round(max(c["t1"] for c in cues) + 0.50, 3)
    return dict(t0=round(t0, 3), t1=t1, xfade=xfade, seed=seed, palette=palette,
                glitch=list(glitch), grade=grade, trans_in=trans, cam=cam,
                caption=cap, anno=anno, layers=layers)


S = shots
# 01 洞穴：BURN 接片头（冷机房过曝到白，白里长洞穴）
S.append(build(18.60 - 0.70, "sepia", WARM,
    [dict(t="bg", src="cave", idx=0, z=1.00, palette="sepia", fit=1.05),
     dict(t="fx", mode="sparks", z=0.46, count=70, alpha=0.9, rise=0.5, seed=71),
     TY(cue("有人用理念构筑", dy=0.02, erase=True)),
     TY(cue("名为本体的神话", dy=0.02, erase=True)),
     dict(t="figure", src="fig_plato", z=0.26, x=0.855, y=0.55, h=0.74, front=True,
          tin=19.6, tout=23.2, alpha=0.92)],
    dict(seed=3, handheld=1.0, aperture=2.0, max_blur=4,
         keys=[(0.0, -0.010, 0.0, 0.000, 0.0, 0.55),
               (0.5, 0.000, 0.004, 0.030, 0.08, 0.55),
               (1.0, 0.006, 0.008, 0.058, 0.16, 0.55)]),
    dict(no="PLATE 01", txt="洞穴 · 火与影", yr="前 4 世纪"),
    dict(t="理念", latin="EIDOS"), seed=11, trans="burn", xfade=0.70))

# 02 学园：CUT（明暗接得上，不重叠）
S.append(build(S[-1]["t1"], "steel", COLD,
    [dict(t="bg", src="academy", idx=0, z=1.00, palette="steel", fit=1.06),
     dict(t="fx", mode="dust", z=0.56, count=110, alpha=0.42, speed=0.03, seed=72),
     dict(t="map", src="map_ancient", z=0.42, x=0.30, y=0.60, w=0.44, rot=-8,
          rot_speed=1.5, alpha=0.60, u_in=0.10),
     TY(cue("逻各斯随波流转", dy=0.10, erase=True)),
     TY(cue("直至阿卡德米亚", dy=0.10, erase=True))],
    dict(seed=5, handheld=1.0, aperture=1.8, max_blur=4,
         keys=[(0.0, 0.014, 0.0, 0.045, 0.14, 0.42),
               (0.5, 0.000, 0.004, 0.020, 0.0, 0.42),
               (1.0, -0.018, 0.008, 0.000, -0.14, 0.42)]),
    dict(no="PLATE 02", txt="学园 · 柱廊", yr="前 387"),
    dict(t="逻各斯", latin="LOGOS"), seed=13, trans=None, xfade=0.0))

# 03 洞穴囚禁：FLASH 黑
S.append(build(S[-1]["t1"] - 0.25, "cold", dict(key=(255, 150, 96), amount=0.26, contrast=1.02, lift=0.05),
    [dict(t="bg", src="cave", idx=1, z=1.00, palette="cold", fit=1.10, alpha=0.52),
     dict(t="fx", mode="dust", z=0.50, count=90, alpha=0.30, speed=0.016, seed=73),
     dict(t="prop", src="bound_figure", z=0.34, x=0.50, y=0.58, h=0.64),
     TY(cue("洞穴里有人囚禁", dy=0.20, erase=True)),
     TY(cue("有人指认出虚华", dy=0.20, erase=True))],
    dict(seed=7, handheld=0.5, aperture=1.4, max_blur=3,
         keys=[(0.0, 0.0, 0.0, 0.004, 0.0, 0.34),
               (0.5, 0.002, 0.0, 0.008, 0.02, 0.34),
               (1.0, 0.004, 0.0, 0.014, 0.06, 0.34)]),
    dict(no="PLATE 03", txt="洞喻 · 被缚者", yr="前 4 世纪"),
    dict(t="囚禁", latin="SPELUNCA"), seed=17, trans="flash_black", xfade=0.25))

# 04 毒杯：PUSH（同一空间感）
S.append(build(S[-1]["t1"] - 0.55, "sepia", WARM,
    [dict(t="bg", src="hemlock", idx=0, z=1.00, palette="sepia", fit=1.04),
     dict(t="prop", src="hand_cup", z=0.30, x=0.68, y=0.60, h=0.72),
     dict(t="fx", mode="smoke", z=0.42, count=6, alpha=0.16, seed=74),
     TY(cue("也有人饮下毒鸩", dy=0.06, erase=True)),
     TY(cue("将死生从容作答", dy=0.06, erase=True)),
     dict(t="figure", src="fig_socrates", z=0.25, x=0.20, y=0.50, h=0.66, front=True,
          tin=32.6, tout=35.4, alpha=0.90)],
    dict(seed=11, handheld=0.3, aperture=0.0, max_blur=0,
         keys=[(0.0, 0.0, 0.0, 0.0, 0.0, 0.30),
               (0.5, 0.0, 0.0, 0.0, 0.0, 0.30),
               (1.0, 0.0, 0.0, 0.0, 0.0, 0.30)]),
    dict(no="PLATE 04", txt="毒芹之杯", yr="前 399"),
    dict(t="毒鸩", latin="PHARMAKON"), seed=23, trans="push", xfade=0.55))

# 05 天城：RISE
S.append(build(S[-1]["t1"] - 0.55, "gold", GOLD,
    [dict(t="bg", src="celestial", idx=0, z=1.00, palette="gold", fit=1.05),
     dict(t="fx", mode="dust", z=0.54, count=130, alpha=0.40, speed=0.028, seed=75),
     TY(cue("神谕中有座天城", kind="line", layout="up_center", px=116, vertical=True,
            dy=-0.04, erase=True)),
     TY(cue("托名唤作耶和华", dy=0.20, erase=True))],
    dict(seed=13, handheld=0.9, aperture=1.6, max_blur=4,
         keys=[(0.0, 0.0, 0.026, 0.018, 0.0, 0.55),
               (0.5, 0.004, 0.000, 0.034, 0.06, 0.55),
               (1.0, 0.008, -0.028, 0.050, 0.12, 0.55)]),
    dict(no="PLATE 05", txt="上帝之城", yr="426"),
    dict(t="天城", latin="CIVITAS DEI"), seed=29, trans="rise", xfade=0.55))

# 06 抄经房：CUT
S.append(build(S[-1]["t1"], "gold", GOLD,
    [dict(t="bg", src="scriptorium", idx=0, z=1.00, palette="gold", fit=1.05),
     dict(t="fx", mode="paper", z=0.46, count=7, alpha=0.55, seed=76),
     dict(t="prop", src="scholar_desk", z=0.34, x=0.44, y=0.52, h=0.86),
     TY(cue("有位手持信理的", dy=0.18, erase=True)),
     TY(cue("托马斯意气风发", dy=-0.14, erase=True)),
     dict(t="figure", src="fig_aquinas", z=0.24, x=0.83, y=0.50, h=0.70, front=True,
          tin=40.2, tout=43.4, alpha=0.90)],
    dict(seed=15, handheld=1.0, aperture=2.6, max_blur=6,
         keys=[(0.0, 0.0, 0.0, 0.0, 0.0, 0.34),
               (0.55, 0.004, -0.004, 0.040, 0.08, 0.34),
               (1.0, 0.010, -0.008, 0.072, 0.16, 0.72)]),
    dict(no="PLATE 06", txt="抄经院", yr="13 世纪"),
    dict(t="信理", latin="DOGMA"), seed=31, trans=None, xfade=0.0))

# 07 对峙：TRUCK（同一房间）
S.append(build(S[-1]["t1"] - 0.55, "gold", GOLD,
    [dict(t="bg", src="disputation", idx=0, z=1.00, palette="gold", fit=1.05),
     dict(t="fx", mode="shaft", z=0.60, angle=-18, center=0.4, amt=0.30, drift=0.10, u_in=0.0),
     dict(t="figure", src="fig_plato", z=0.30, x=0.22, y=0.50, h=0.44,
          tin=44.0, tout=47.2, alpha=0.80),
     dict(t="figure", src="fig_kant", z=0.40, x=0.78, y=0.48, h=0.40,
          tin=44.3, tout=47.2, alpha=0.72),
     TY(cue("唯名与唯实交锋", kind="collide", dy=0.08, erase=True)),
     TY(cue("将思辨翻覆揉轧", kind="shuffle", dy=0.08, erase=True))],
    dict(seed=17, handheld=0.7, aperture=0.0, max_blur=0,
         keys=[(0.0, -0.030, 0.0, 0.006, -0.10, 0.55),
               (0.5, 0.000, 0.0, 0.010, 0.00, 0.55),
               (1.0, 0.030, 0.0, 0.014, 0.10, 0.55)]),
    dict(no="PLATE 07", txt="共相之争", yr="12 世纪"),
    dict(t="唯名", latin="NOMEN"), seed=37, trans="truck", xfade=0.55))

# 08 玫瑰窗：WHIP
S.append(build(S[-1]["t1"] - 0.30, "gold", GOLD,
    [dict(t="bg", src="rose", idx=0, z=1.00, palette="gold", fit=1.04),
     dict(t="fx", mode="dust", z=0.52, count=120, alpha=0.40, speed=0.024, seed=77),
     dict(t="texture", mode="scanline", z=0.28, front=True, alpha=0.55, speed=0.8,
          width=0.0016, u_in=0.0),
     TY(cue("辩驳里有谁将信仰", kind="line", layout="right_v", px=116, vertical=True,
            erase=True)),
     TY(cue("用理性来传达", dy=0.18, erase=True))],
    dict(seed=19, handheld=0.8, aperture=1.8, max_blur=4,
         keys=[(0.0, 0.0, 0.0, 0.018, 0.0, 0.55),
               (0.5, 0.004, 0.004, 0.034, 0.06, 0.55),
               (1.0, 0.008, 0.006, 0.052, 0.10, 0.55)]),
    dict(no="PLATE 08", txt="玫瑰窗", yr="13 世纪"),
    dict(t="信仰", latin="FIDES"), seed=41, trans="whip", xfade=0.30))

json.dump(shots, open(os.path.join(HERE, "shots_v10.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("shots", len(shots), "->", shots[-1]["t1"], "s")
for s in shots[-8:]:
    print("  %6.2f-%6.2f  %-14s  trans=%s xf=%.2f" %
          (s["t0"], s["t1"], s.get("caption", {}).get("txt", ""), s.get("trans_in"), s["xfade"]))

