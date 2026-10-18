# -*- coding: utf-8 -*-
"""Opening 10 era cards + shots 01-08.

Rules enforced here:
  * every cue ends inside its shot (shot.t1 = max(cue.t1) + 0.5)
  * lyric text is a wide thin band, justified, sitting in the dark part
  * no punctuation, no extreme skew
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

WARM = dict(key=(255, 152, 96), amount=0.34, contrast=1.06, lift=-0.01)
COLD = dict(key=(190, 212, 238), amount=0.30, contrast=1.05, lift=0.0)
GOLD = dict(key=(238, 196, 128), amount=0.30, contrast=1.03, lift=0.01)
DIM = dict(key=(226, 200, 178), amount=0.22, contrast=1.00, lift=0.0)


def mk_cue(text, kind="band", layout=None, px=None, **kw):
    key = PUNCT.sub("", text)
    r = BY.get(key)
    t0 = kw.pop("t0", None)
    t1 = kw.pop("t1", None)
    if r is None:
        if t0 is None:
            raise KeyError(key)
        base = dict(t0=t0, t1=t1 if t1 is not None else t0 + 3.0)
        words = []
    else:
        base = dict(t0=r["t0"], t1=r["t1"] + 0.30)
        words = [{"t0": w["t0"]} for w in r["words"]]
    c = dict(kind=kind, text=key, t0=base["t0"], t1=base["t1"],
             layout=layout or "center", px=px, words=words, glow=0.45,
             seed=abs(hash(key)) % 9999)
    c.update(kw)
    return c


def T(c, z=0.30):
    return dict(t="type", z=z, cue=c)


shots = []

# ---------------------------------------------------------------- 10 era cards
CARD = 18.90 / len(ERA)
for i, (key, name, sub) in enumerate(ERA):
    a = round(i * CARD, 3)
    b = round((i + 1) * CARD, 3)
    shots.append(dict(
        t0=a, t1=b, seed=(100 + i) & 0xFFFF, palette="sepia", glitch=[0.03, 0.06],
        grade=DIM if i % 2 else dict(key=(236, 210, 180), amount=0.26, contrast=1.04, lift=0.0),
        trans_in=("flash" if i else "flash_soft"),
        cam=dict(seed=i, handheld=0.7, aperture=0.0, max_blur=0,
                 keys=[(0.0, -0.006, 0.000, 0.000, 0.0, 0.55),
                       (1.0, 0.006, 0.002, 0.035, 0.10, 0.55)]),
        caption=None, anno=None,
        layers=[
            dict(t="bg", src=key, idx=0, z=1.00, palette="sepia", fit=1.02),
            dict(t="type", z=0.32, cue=mk_cue("%02d / 10" % (i + 1), kind="note",
                                              layout="top_left", px=24, alpha=0.62,
                                              t0=a + 0.18, t1=b - 0.05)),
            dict(t="type", z=0.30, cue=mk_cue(name, kind="band", px=138, justify=True,
                                              band=0.72, dy=0.10,
                                              t0=a + 0.22, t1=b - 0.02)),
            dict(t="type", z=0.30, cue=mk_cue(sub, kind="note", layout="center", px=30,
                                              alpha=0.85, dy=0.26,
                                              t0=a + 0.36, t1=b - 0.02)),
        ]))


# ---------------------------------------------------------------- shots 01-08
def shot(t0, palette, grade, bg, subjects, cues, cam, caption, anno, glitch=(0.04, 0.12),
         trans=None, seed=7):
    layers = [dict(t="bg", src=bg, idx=0, z=1.00, palette=palette, fit=1.05)]
    layers += subjects
    layers += [T(c) for c in cues]
    cues.sort(key=lambda c: c["t0"])
    for i in range(len(cues) - 1):
        cues[i]["t1"] = min(cues[i]["t1"], cues[i + 1]["t0"] - 0.12)
    t1 = max(c["t1"] for c in cues) + 0.50
    return dict(t0=t0, t1=round(t1, 3), seed=seed, palette=palette, glitch=list(glitch),
                grade=grade, trans_in=trans,
                cam=cam, caption=caption, anno=anno, layers=layers)


def subj(src, z, x, y, h, **kw):
    d = dict(t="prop", src=src, z=z, x=x, y=y, h=h)
    d.update(kw)
    return d


shots.append(shot(
    18.90, "sepia", WARM, "cave",
    [subj("brazier", 0.62, 0.24, 0.74, 0.34)],
    [mk_cue("有人用理念构筑", dy=0.16),
     mk_cue("名为本体的神话", dy=0.16)],
    dict(seed=3, handheld=1.0, aperture=2.2, max_blur=5,
         keys=[(0.0, 0.000, 0.000, 0.000, 0.0, 0.60),
               (1.0, 0.006, 0.008, 0.060, 0.18, 0.60)]),
    dict(no="PLATE 01", txt="洞穴 · 火与影", yr="前 4 世纪"),
    dict(t="理念", latin="EIDOS"), seed=11))

shots.append(shot(
    shots[-1]["t1"] + 0.02, "steel", COLD, "academy",
    [],
    [mk_cue("逻各斯随波流转", dy=0.12),
     mk_cue("直至阿卡德米亚", dy=0.12)],
    dict(seed=5, handheld=1.0, aperture=1.8, max_blur=4,
         keys=[(0.0, -0.014, 0.000, 0.050, -0.18, 0.55),
               (1.0, 0.020, 0.004, 0.000, 0.16, 0.55)]),
    dict(no="PLATE 02", txt="学园 · 柱廊", yr="前 387"),
    dict(t="逻各斯", latin="LOGOS"), seed=13))

shots.append(shot(
    shots[-1]["t1"] + 0.02, "cold", WARM, "cave",
    [dict(t="bg", src="cave", idx=1, z=1.00, palette="cold", fit=1.10, alpha=0.16),
     subj("bound_figure", 0.34, 0.50, 0.58, 0.62)],
    [mk_cue("洞穴里有人囚禁", dy=0.20),
     mk_cue("有人指认出虚华", dy=0.20)],
    dict(seed=7, handheld=0.5, aperture=1.6, max_blur=4,
         keys=[(0.0, 0.000, 0.000, 0.004, 0.0, 0.34),
               (1.0, 0.002, 0.000, 0.012, 0.08, 0.34)]),
    dict(no="PLATE 03", txt="洞喻 · 被缚者", yr="前 4 世纪"),
    dict(t="囚禁", latin="SPELUNCA"), seed=17))

shots.append(shot(
    shots[-1]["t1"] + 0.02, "sepia", WARM, "hemlock",
    [subj("hand_cup", 0.30, 0.68, 0.60, 0.74)],
    [mk_cue("也有人饮下毒鸩", dy=0.06),
     mk_cue("将死生从容作答", dy=0.06)],
    dict(seed=11, handheld=0.4, aperture=0.0, max_blur=0,
         keys=[(0.0, 0.0, 0.0, 0.0, 0.0, 0.30),
               (1.0, 0.0, 0.0, 0.0, 0.0, 0.30)]),
    dict(no="PLATE 04", txt="毒芹之杯", yr="前 399"),
    dict(t="毒鸩", latin="PHARMAKON"), seed=23))

shots.append(shot(
    shots[-1]["t1"] + 0.02, "gold", GOLD, "celestial",
    [],
    [mk_cue("神谕中有座天城", kind="line", layout="up_center", px=118, vertical=True, dy=-0.04),
     mk_cue("托名唤作耶和华", dy=0.20)],
    dict(seed=13, handheld=0.9, aperture=1.8, max_blur=4,
         keys=[(0.0, 0.000, 0.020, 0.020, 0.0, 0.55),
               (1.0, 0.006, -0.028, 0.050, 0.14, 0.55)]),
    dict(no="PLATE 05", txt="上帝之城", yr="426"),
    dict(t="天城", latin="CIVITAS DEI"), seed=29))

shots.append(shot(
    shots[-1]["t1"] + 0.02, "gold", GOLD, "scriptorium",
    [subj("scholar_desk", 0.34, 0.46, 0.52, 0.86)],
    [mk_cue("有位手持信理的", dy=0.18),
     mk_cue("托马斯意气风发", dy=-0.16)],
    dict(seed=15, handheld=1.0, aperture=3.0, max_blur=7,
         keys=[(0.0, 0.000, 0.000, 0.000, 0.0, 0.34),
               (0.55, 0.004, -0.004, 0.040, 0.10, 0.34),
               (1.0, 0.010, -0.008, 0.075, 0.18, 0.80)]),
    dict(no="PLATE 06", txt="抄经院", yr="13 世纪"),
    dict(t="信理", latin="DOGMA"), seed=31))

shots.append(shot(
    shots[-1]["t1"] + 0.02, "gold", GOLD, "disputation",
    [],
    [mk_cue("唯名与唯实交锋", kind="collide", dy=0.10),
     mk_cue("将思辨翻覆揉轧", kind="shuffle", dy=0.10)],
    dict(seed=17, handheld=0.7, aperture=0.0, max_blur=0,
         keys=[(0.0, 0.0, 0.0, 0.004, 0.0, 0.55), (1.0, 0.0, 0.0, 0.008, 0.0, 0.55)]),
    dict(no="PLATE 07", txt="共相之争", yr="12 世纪"),
    dict(t="唯名", latin="NOMEN"), seed=37))

shots.append(shot(
    shots[-1]["t1"] + 0.02, "gold", GOLD, "rose",
    [],
    [mk_cue("辩驳里有谁将信仰", kind="line", layout="right_v", px=118, vertical=True),
     mk_cue("用理性来传达", kind="band", dy=0.18)],
    dict(seed=19, handheld=0.8, aperture=2.0, max_blur=5,
         keys=[(0.0, 0.000, 0.000, 0.020, 0.0, 0.55),
               (1.0, 0.008, 0.006, 0.055, 0.12, 0.55)]),
    dict(no="PLATE 08", txt="玫瑰窗", yr="13 世纪"),
    dict(t="信仰", latin="FIDES"), seed=41, trans="flash"))

json.dump(shots, open(os.path.join(HERE, "shots_open8.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("shots", len(shots), "| 0 →", shots[-1]["t1"], "s")
for s in shots[-8:]:
    print("  %6.2f-%6.2f  %s" % (s["t0"], s["t1"], s.get("caption", {}).get("txt", "")))



