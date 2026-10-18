# -*- coding: utf-8 -*-
"""v14: opening + scenes 1-8.

  * opening cards carry the era NAME only (the sub-line is gone)
  * every hand-over is a LINK: the outgoing shot and the incoming shot really
    overlap, A walks out as B walks in, so nothing between them is ever empty
  * links vary in direction (left / up / down / diagonal), carry a push and
    sometimes a roll; all bezier eased; no cuts, no white flashes, no bars
  * inside a scene every lyric line still nudges the camera (medium size)
"""
import json, io, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PUNCT = re.compile(r'[\s\u3000"\u201c\u201d\'\u2018\u2019,，.。!！?？;；:：、]')

rows = json.load(io.open(os.path.join(HERE, "timing_auto.json"), encoding="utf-8"))
BY = {PUNCT.sub("", r["text"]): r for r in rows}

ERA = [
    ("era01_ionia", "古希腊早期哲学"),
    ("era02_cave_academy", "古希腊古典哲学"),
    ("era03_gothic", "中古哲学"),
    ("era04_slate_mirror", "经验论与唯理论"),
    ("era05_bastille", "法国大革命"),
    ("era06_factory_book", "马克思主义"),
    ("era07_winterpalace", "十月革命"),
    ("era08_lab", "实用主义"),
    ("era09_logic_board", "分析哲学"),
    ("era10_machine", "人工智能哲学"),
]
WARM = dict(key=(255, 152, 96), amount=0.34, contrast=1.07, lift=-0.012)
COLD = dict(key=(188, 210, 238), amount=0.30, contrast=1.06, lift=0.0)
GOLD = dict(key=(238, 196, 128), amount=0.30, contrast=1.04, lift=0.008)
ASH = dict(key=(226, 214, 196), amount=0.26, contrast=1.03, lift=0.004)
RED = dict(key=(216, 108, 82), amount=0.40, contrast=1.07, lift=-0.008)
RED_DEEP = dict(key=(198, 84, 66), amount=0.46, contrast=1.09, lift=-0.014)

shots = []

# ---------------------------------------------------------------- opening
X, CARD = 0.60, 2.40
for i, (key, name) in enumerate(ERA):
    a = round(i * (CARD - X), 3)
    b = round(min(a + CARD, 18.90), 3)
    z0 = 0.012 + i * 0.012
    cam = dict(seed=20 + i, handheld=1.2, aperture=1.4, max_blur=5, dur=b - a,
               keys=[(0.0, -0.016 + 0.003 * i, 0.006, z0, -0.26 + 0.04 * i, 0.62),
                     (0.45, 0.002, 0.000, z0 + 0.060, 0.01, 0.62),
                     (1.0, 0.018, -0.006, z0 + 0.112, 0.22 - 0.04 * i, 0.62)])
    layers = [
        dict(t="bg", src=key, idx=0, z=1.00, palette="sepia", fit=1.06),
        dict(t="fx", mode="dust", z=0.55, count=60 + i * 5, alpha=0.36, speed=0.026, seed=60 + i),
        dict(t="type", z=0.30, cue=dict(kind="band", text=name, t0=a + 0.35, t1=b - 0.15,
                                        layout="center", px=132, justify=True, band=0.72,
                                        dy=0.06, erase=True, words=[], glow=0.45, seed=100 + i)),
    ]
    if i in (1, 8):
        layers.insert(2, dict(t="map", src="map_ancient", z=0.44, x=0.26, y=0.62, w=0.32,
                              rot=-7, rot_speed=1.8, alpha=0.38, u_in=0.20, seed=3))
    if i == 4:
        layers.insert(2, dict(t="prop", src="flag_fr", z=0.34, x=0.76, y=0.50, h=0.74,
                              tilt=-8, alpha=0.55))
    if i == 5:
        layers.insert(2, dict(t="prop", src="flag_red", z=0.40, x=0.20, y=0.46, h=0.58,
                              tilt=9, flip=True, alpha=0.40))
    if i == 6:
        layers.insert(2, dict(t="prop", src="flag_red", z=0.30, x=0.84, y=0.46, h=0.96,
                              tilt=-4, alpha=0.52))
    shots.append(dict(t0=a, t1=b, xfade=X if i else 0.0, seed=100 + i, palette="sepia",
                      glitch=[0.03, 0.07], link=None,
                      grade=(RED if i == 4 else RED_DEEP if i in (5, 6) else ASH),
                      cam=cam,
                      tr_in=dict(kind="spin", amt=1.20, deg=-6.0, ramp=0.34) if i else None,
                      caption=None, anno=None, layers=layers, _cue_end=b - 0.15))


# ---------------------------------------------------------------- scenes
def cue(text, kind="band", layout=None, px=None, **kw):
    key = PUNCT.sub("", text)
    r = BY.get(key)
    t0 = kw.pop("t0", None); t1 = kw.pop("t1", None)
    if r is None:
        base = dict(t0=t0, t1=t1 if t1 is not None else t0 + 3.0); words = []
    else:
        base = dict(t0=r["t0"], t1=r["t1"] + 0.30)
        words = [{"t0": w["t0"]} for w in r["words"]]
    c = dict(kind=kind, text=key, t0=base["t0"], t1=base["t1"],
             layout=layout or "center", px=px, words=words, glow=0.45,
             seed=abs(hash(key)) % 9999)
    c.update(kw)
    return c


def TY(c, z=0.30):
    return dict(t="type", z=z, cue=c)


S = shots


def build(link, palette, grade, layers, cam, cap, anno, seed,
          glitch=(0.04, 0.12), tail=0.70):
    """Append a scene. `link` describes the hand-over from the previous shot:
    both shots overlap for `dur`, A leaving along `out` while B arrives.

    The overlap is placed inside the silence between the two lines: A's last
    caption must have finished fading, B's first caption must not start more
    than a hair before the whip lands.
    """
    prev = S[-1] if S else None
    cues = [L["cue"] for L in layers if L.get("t") == "type"]
    cues.sort(key=lambda c: c["t0"])
    for i in range(len(cues) - 1):
        cues[i]["t1"] = min(cues[i]["t1"], cues[i + 1]["t0"] - 0.12)
    t1 = round(max(c["t1"] for c in cues) + tail, 3)
    lk = None
    if prev is None or link is None:
        t0 = round(cues[0]["t0"] - 1.20, 3)
    else:
        dur = float(link["dur"])
        tb = cues[0]["t0"]
        lo = prev["_cue_end"] - dur          # A's caption finishes inside A
        hi = tb + 0.15 - dur                 # B's line starts ~with the landing
        want = tb - dur - 0.25               # aim to land before the new line
        t0 = round((lo + hi) * 0.5 if lo > hi else min(max(want, lo), hi), 3)
        lk = dict(dur=dur, out=link["out"], prev=len(S) - 1,
                  za=float(link.get("za", 1.0)), zb=float(link.get("zb", 1.0)),
                  ra=float(link.get("ra", 0.0)), rb=float(link.get("rb", 0.0)))
        prev["t1"] = round(t0 + dur, 3)
        prev["cam"]["dur"] = round(prev["t1"] - prev["t0"], 3)
    cam["dur"] = round(t1 - t0, 3)
    nd = []
    for i, c in enumerate(cues[1:]):
        sgn = 1 if i % 2 == 0 else -1
        nd.append(dict(t=c["t0"] - t0, w=0.30,
                       dx=0.012 * sgn, dy=-0.006, dz=0.016, dr=0.14 * sgn))
    cam["nudges"] = nd
    return dict(t0=t0, t1=t1, xfade=0.0, seed=seed, palette=palette,
                glitch=list(glitch), grade=grade, cam=cam, link=lk,
                tr_in=None, caption=cap, anno=anno, layers=layers,
                _cue_end=round(max(c["t1"] for c in cues), 3))


def add(link, *a, **kw):
    S.append(build(link, *a, **kw))


# 01 洞穴 · 理念：向左甩出 → 学园从右侧推入
add(dict(out="left", dur=0.55, za=1.20, ra=-3),
    "sepia", WARM,
    [dict(t="bg", src="cave", idx=0, z=1.00, palette="sepia", fit=1.05),
     dict(t="fx", mode="sparks", z=0.46, count=70, alpha=0.9, rise=0.5, seed=71),
     TY(cue("有人用理念构筑", dy=0.02, erase=True)),
     TY(cue("名为本体的神话", dy=0.02, erase=True)),
     dict(t="figure", src="fig_plato", z=0.26, x=0.855, y=0.55, h=0.74, front=True,
          tin=19.6, tout=23.2, alpha=0.92, seed=5)],
    dict(seed=3, handheld=1.2, aperture=2.0, max_blur=4,
         keys=[(0.0, -0.014, 0.002, 0.000, -0.04, 0.55),
               (0.5, 0.002, 0.006, 0.030, 0.10, 0.55),
               (1.0, 0.010, 0.010, 0.058, 0.20, 0.55)]),
    dict(no="PLATE 01", txt="洞穴 · 火与影", yr="前 4 世纪"),
    dict(t="理念", latin="EIDOS"), seed=11)

# 02 学园 · 柱廊：向上抬起 → 洞喻从下方升起
add(dict(out="up", dur=0.50, za=1.10, ra=4),
    "steel", COLD,
    [dict(t="bg", src="academy", idx=0, z=1.00, palette="steel", fit=1.06),
     dict(t="fx", mode="dust", z=0.56, count=110, alpha=0.42, speed=0.03, seed=72),
     TY(cue("逻各斯随波流转", dy=0.10, erase=True)),
     TY(cue("直至阿卡德米亚", dy=0.10, erase=True))],
    dict(seed=5, handheld=1.3, aperture=1.8, max_blur=4,
         keys=[(0.0, 0.014, 0.014, 0.030, 0.16, 0.42),
               (0.5, 0.000, 0.006, 0.014, 0.0, 0.42),
               (1.0, -0.020, 0.010, -0.006, -0.18, 0.42)]),
    dict(no="PLATE 02", txt="学园 · 柱廊", yr="前 387"),
    dict(t="逻各斯", latin="LOGOS"), seed=13)

# 03 洞喻 · 被缚者：斜向左下退出 → 毒杯从左上来
add(dict(out="dl", dur=0.55, za=1.14, ra=-3),
    "cold", dict(key=(255, 150, 96), amount=0.26, contrast=1.02, lift=0.05),
    [dict(t="bg", src="cave", idx=1, z=1.00, palette="cold", fit=1.10, alpha=0.52),
     dict(t="fx", mode="dust", z=0.50, count=90, alpha=0.30, speed=0.016, seed=73),
     dict(t="prop", src="bound_figure", z=0.34, x=0.50, y=0.58, h=0.64),
     TY(cue("洞穴里有人囚禁", dy=0.20, erase=True)),
     TY(cue("有人指认出虚华", dy=0.20, erase=True))],
    dict(seed=7, handheld=0.7, aperture=1.4, max_blur=3,
         keys=[(0.0, 0.0, 0.0, 0.004, 0.0, 0.34),
               (0.5, 0.003, 0.002, 0.010, 0.03, 0.34),
               (1.0, 0.006, 0.004, 0.018, 0.08, 0.34)]),
    dict(no="PLATE 03", txt="洞喻 · 被缚者", yr="前 4 世纪"),
    dict(t="囚禁", latin="SPELUNCA"), seed=17)

# 04 毒芹之杯：向下坠落 → 天城自上方垂落
add(dict(out="down", dur=0.46, za=1.08),
    "sepia", WARM,
    [dict(t="bg", src="hemlock", idx=0, z=1.00, palette="sepia", fit=1.04),
     dict(t="prop", src="hand_cup", z=0.30, x=0.68, y=0.60, h=0.72),
     dict(t="fx", mode="smoke", z=0.42, count=6, alpha=0.16, seed=74),
     TY(cue("也有人饮下毒鸩", dy=0.06, erase=True)),
     TY(cue("将死生从容作答", dy=0.06, erase=True)),
     dict(t="figure", src="fig_socrates", z=0.25, x=0.20, y=0.50, h=0.66, front=True,
          tin=32.6, tout=35.4, alpha=0.90, seed=7)],
    dict(seed=11, handheld=0.4, aperture=0.0, max_blur=0,
         keys=[(0.0, 0.0, 0.0, 0.0, 0.0, 0.30),
               (0.5, 0.0, 0.0, 0.0, 0.0, 0.30),
               (1.0, 0.0, 0.0, 0.0, 0.0, 0.30)]),
    dict(no="PLATE 04", txt="毒芹之杯", yr="前 399"),
    dict(t="毒鸩", latin="PHARMAKON"), seed=23)

# 05 天城：向右甩出、略微回缩 → 抄经房从左侧拉开进入
add(dict(out="right", dur=0.52, za=1.0, zb=1.14),
    "gold", GOLD,
    [dict(t="bg", src="celestial", idx=0, z=1.00, palette="gold", fit=1.05),
     dict(t="fx", mode="dust", z=0.54, count=130, alpha=0.40, speed=0.028, seed=75),
     TY(cue("神谕中有座天城", kind="line", layout="up_center", px=116, vertical=True,
            dy=-0.04, erase=True)),
     TY(cue("托名唤作耶和华", dy=0.20, erase=True))],
    dict(seed=13, handheld=1.0, aperture=1.6, max_blur=4,
         keys=[(0.0, 0.0, 0.030, 0.018, 0.0, 0.55),
               (0.5, 0.006, 0.000, 0.036, 0.08, 0.55),
               (1.0, 0.012, -0.032, 0.056, 0.18, 0.55)]),
    dict(no="PLATE 05", txt="上帝之城", yr="426"),
    dict(t="天城", latin="CIVITAS DEI"), seed=29)

# 06 抄经院：斜向左上带滚转退出 → 对峙自右下翻入
add(dict(out="ul", dur=0.55, za=1.16, ra=-6, rb=6),
    "gold", GOLD,
    [dict(t="bg", src="scriptorium", idx=0, z=1.00, palette="gold", fit=1.05),
     dict(t="fx", mode="paper", z=0.46, count=7, alpha=0.55, seed=76),
     dict(t="prop", src="scholar_desk", z=0.34, x=0.44, y=0.52, h=0.86),
     TY(cue("有位手持信理的", dy=0.18, erase=True)),
     TY(cue("托马斯意气风发", dy=-0.14, erase=True)),
     dict(t="figure", src="fig_aquinas", z=0.24, x=0.83, y=0.50, h=0.70, front=True,
          tin=40.2, tout=43.4, alpha=0.90, seed=9)],
    dict(seed=15, handheld=1.2, aperture=2.6, max_blur=6,
         keys=[(0.0, 0.0, 0.0, 0.000, 0.0, 0.34),
               (0.55, 0.006, -0.006, 0.038, 0.10, 0.34),
               (1.0, 0.014, -0.012, 0.072, 0.20, 0.72)]),
    dict(no="PLATE 06", txt="抄经院", yr="13 世纪"),
    dict(t="信理", latin="DOGMA"), seed=31)

# 07 共相之争：向左强力甩出 → 玫瑰窗自右侧推入
add(dict(out="left", dur=0.50, za=1.26, ra=3),
    "gold", GOLD,
    [dict(t="bg", src="disputation", idx=0, z=1.00, palette="gold", fit=1.05),
     dict(t="fx", mode="shaft", z=0.60, angle=-18, center=0.4, amt=0.30, drift=0.10, u_in=0.0),
     dict(t="figure", src="fig_plato", z=0.30, x=0.22, y=0.50, h=0.44,
          tin=44.0, tout=47.2, alpha=0.80, seed=11),
     dict(t="figure", src="fig_kant", z=0.40, x=0.78, y=0.48, h=0.40,
          tin=44.3, tout=47.2, alpha=0.72, seed=12),
     TY(cue("唯名与唯实交锋", kind="collide", dy=0.08, erase=True)),
     TY(cue("将思辨翻覆揉轧", kind="shuffle", dy=0.08, erase=True))],
    dict(seed=17, handheld=0.9, aperture=0.0, max_blur=0,
         keys=[(0.0, -0.038, 0.0, 0.004, -0.14, 0.55),
               (0.5, 0.000, 0.0, 0.012, 0.00, 0.55),
               (1.0, 0.038, 0.0, 0.018, 0.14, 0.55)]),
    dict(no="PLATE 07", txt="共相之争", yr="12 世纪"),
    dict(t="唯名", latin="NOMEN"), seed=37)

# 08 玫瑰窗：斜向右下退出（本段收束）
add(dict(out="dr", dur=0.55, za=1.12, ra=-4),
    "gold", GOLD,
    [dict(t="bg", src="rose", idx=0, z=1.00, palette="gold", fit=1.04),
     dict(t="fx", mode="dust", z=0.52, count=120, alpha=0.40, speed=0.024, seed=77),
     dict(t="texture", mode="scanline", z=0.28, front=True, alpha=0.55, speed=0.8,
          width=0.0016, u_in=0.0),
     TY(cue("辩驳里有谁将信仰", kind="line", layout="right_v", px=116, vertical=True,
            erase=True)),
     TY(cue("用理性来传达", dy=0.18, erase=True))],
    dict(seed=19, handheld=1.0, aperture=1.8, max_blur=4,
         keys=[(0.0, 0.0, 0.0, 0.018, 0.0, 0.55),
               (0.5, 0.005, 0.006, 0.034, 0.08, 0.55),
               (1.0, 0.010, 0.008, 0.054, 0.14, 0.55)]),
    dict(no="PLATE 08", txt="玫瑰窗", yr="13 世纪"),
    dict(t="信仰", latin="FIDES"), seed=41)

json.dump(shots, open(os.path.join(HERE, "shots_v13.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("shots", len(shots), "->", shots[-1]["t1"], "s")
for s in shots[-8:]:
    print("  %6.2f-%6.2f %-13s link=%-12s dur=%s nudge=%d" %
          (s["t0"], s["t1"], s.get("caption", {}).get("txt", ""),
           (s.get("link") or {}).get("out"), (s.get("link") or {}).get("dur"),
           len(s["cam"].get("nudges") or [])))
