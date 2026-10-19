# -*- coding: utf-8 -*-
"""v15 — the whole film: opening (10 era cards) + shots 01-41 + tail.

Rules this file encodes
  * no cut, no white flash, no BURN: every hand-over is a LINK, i.e. the two
    shots really overlap for `dur` and A walks out while B walks in
  * the link window sits in the silence between two sung lines: A's caption
    must be finished, B's must not start more than a hair early
  * a camera can push in or pull out inside a shot wherever the content asks
    for it (z 0 -> 0.10 = dolly in, 0.10 -> 0 = dolly out), with a focus rack
  * every caption holds its last glyph for >= 0.5 s after it appears
"""
import json, io, os, re, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PUNCT = re.compile(r'[\s\u3000"\u201c\u201d\'\u2018\u2019,，.。!！?？;；:：、]')

rows = json.load(io.open(os.path.join(HERE, "timing_auto.json"), encoding="utf-8"))
BY = {PUNCT.sub("", r["text"]): r for r in rows}

# ---------------------------------------------------------------- palettes
WARM = dict(key=(255, 152, 96), amount=0.34, contrast=1.07, lift=-0.012)
COLD = dict(key=(188, 210, 238), amount=0.30, contrast=1.06, lift=0.0)
GOLD = dict(key=(238, 196, 128), amount=0.30, contrast=1.04, lift=0.008)
ASH = dict(key=(226, 214, 196), amount=0.26, contrast=1.03, lift=0.004)
RED = dict(key=(216, 108, 82), amount=0.40, contrast=1.07, lift=-0.008)
RED_DEEP = dict(key=(198, 84, 66), amount=0.46, contrast=1.09, lift=-0.014)
BONE = dict(key=(255, 247, 232), amount=0.32, contrast=1.02, lift=0.055)

shots = []

# ================================================================ opening
ERA = [
    ("era01_ionia", "古希腊早期哲学", ASH),
    ("era02_cave_academy", "古希腊古典哲学", ASH),
    ("era03_gothic", "中古哲学", ASH),
    ("era04_slate_mirror", "经验论与唯理论", ASH),
    ("era05_liberte", "法国大革命", RED),
    ("era06_factory_book", "马克思主义", RED_DEEP),
    ("era07_winterpalace", "十月革命", RED_DEEP),
    ("era08_lab", "实用主义", ASH),
    ("era09_logic_board", "分析哲学", ASH),
    ("era10_machine", "人工智能哲学", ASH),
]
X, CARD = 0.60, 2.40
for i, (key, name, grd) in enumerate(ERA):
    a = round(i * (CARD - X), 3)
    b = round(min(a + CARD, 18.90), 3)
    z0 = 0.010 + i * 0.010
    cam = dict(seed=20 + i, handheld=1.2, aperture=1.4, max_blur=5, dur=b - a,
               keys=[(0.0, -0.016 + 0.003 * i, 0.006, z0, -0.26 + 0.04 * i, 0.62),
                     (0.45, 0.002, 0.000, z0 + 0.048, 0.01, 0.62),
                     (1.0, 0.018, -0.006, z0 + 0.092, 0.22 - 0.04 * i, 0.62)])
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
    if i == 5:
        layers.insert(2, dict(t="prop", src="flag_red", z=0.40, x=0.20, y=0.46, h=0.58,
                              tilt=9, flip=True, alpha=0.40))
    if i == 6:
        layers.insert(2, dict(t="prop", src="flag_red", z=0.30, x=0.84, y=0.46, h=0.96,
                              tilt=-4, alpha=0.52))
    shots.append(dict(t0=a, t1=b, xfade=X if i else 0.0, seed=100 + i, palette="sepia",
                      glitch=[0.03, 0.07], link=None, grade=grd, cam=cam,
                      tr_in=dict(kind="spin", amt=1.20, deg=-6.0, ramp=0.34) if i else None,
                      caption=None, anno=None, layers=layers, _cue_end=b - 0.15))


# ================================================================ helpers
def cue(text, kind="band", layout=None, px=None, **kw):
    """A lyric line. Word times that the aligner dragged across an instrumental
    gap are pulled back (gap > 2 s = artefact), and the cue is kept alive
    >= 0.5 s after its last glyph appears so that glyph is actually read."""
    key = PUNCT.sub("", text)
    r = BY.get(key)
    if r is None:
        print("!! lyric not in timing_auto:", key)
    t0 = kw.pop("t0", None)
    t1 = kw.pop("t1", None)
    cap = kw.pop("cap", 4.6)
    if r is None:
        base = dict(t0=t0 if t0 is not None else 0.0,
                    t1=t1 if t1 is not None else (t0 or 0.0) + 3.0)
        words = []
    else:
        ws = [dict(t0=float(w["t0"])) for w in (r.get("words") or [])]
        for i in range(1, len(ws)):
            if ws[i]["t0"] - ws[i - 1]["t0"] > 2.0:
                ws[i]["t0"] = ws[i - 1]["t0"] + 0.42
        on = ws[-1]["t0"] if ws else r["t1"]
        end = min(r["t1"], on + 1.30)
        base = dict(t0=r["t0"], t1=max(end + 0.30, on + 0.80))
        if base["t1"] - base["t0"] > cap:
            base["t1"] = base["t0"] + cap
        words = ws
    c = dict(kind=kind, text=key, t0=base["t0"], t1=max(base["t1"], base["t0"] + 0.6),
             layout=layout or "center", px=px, words=words, glow=0.45,
             seed=zlib.crc32(key.encode("utf-8")) % 9999)
    c.update(kw)
    return c


def TY(c, z=0.30):
    return dict(t="type", z=z, cue=c)


def BG(src, idx=0, fit=1.05, palette="sepia", alpha=1.0, z=1.00):
    d = dict(t="bg", src=src, idx=idx, z=z, palette=palette, fit=fit)
    if alpha < 1.0:
        d["alpha"] = alpha
    return d


def PR(src, x, y, h=0.7, z=0.32, **kw):
    d = dict(t="prop", src=src, z=z, x=x, y=y, h=h)
    d.update(kw)
    return d


def FIG(src, x, y, h=0.65, z=0.26, tin=None, tout=None, alpha=0.9, front=False, **kw):
    d = dict(t="figure", src=src, z=z, x=x, y=y, h=h, alpha=alpha, seed=5)
    if tin is not None:
        d["tin"] = tin
    if tout is not None:
        d["tout"] = tout
    if front:
        d["front"] = True
    d.update(kw)
    return d


def FX(mode="dust", z=0.52, count=100, alpha=0.40, seed=71, **kw):
    d = dict(t="fx", mode=mode, z=z, count=count, alpha=alpha, seed=seed)
    d.update(kw)
    return d


def TEX(mode="scanline", z=0.28, alpha=0.5, **kw):
    d = dict(t="texture", mode=mode, z=z, front=True, alpha=alpha, u_in=0.0)
    d.update(kw)
    return d


def CAM(x0=0.0, x1=0.0, y0=0.0, y1=0.0, z0=0.0, z1=0.0, r0=0.0, r1=0.0,
        f0=0.45, f1=0.45, handheld=1.1, aperture=1.8, max_blur=4.5, seed=3, mid=None):
    """z1>z0 = dolly in, z1<z0 = dolly out; f0/f1 = focus rack."""
    keys = [(0.0, x0, y0, z0, r0, f0)]
    if mid:
        keys.append(mid)
    keys.append((1.0, x1, y1, z1, r1, f1))
    keys.sort(key=lambda k: k[0])
    return dict(seed=seed, handheld=handheld, aperture=aperture, max_blur=max_blur, keys=keys)


S = shots

# 微场景风格表：(名字, dx, dy, dz, dr, df)
#   push 推近 / pull 退开 / truck 横移 / rise 升降 / rack 移焦 / roll 甩滚
MICRO = [
    ("push", 0.022, -0.010, 0.030, 0.20, 0.00),
    ("pull", -0.016, 0.008, -0.026, -0.14, 0.00),
    ("truck", 0.030, 0.000, 0.008, 0.08, 0.00),
    ("rise", 0.000, -0.016, 0.014, 0.00, 0.00),
    ("rack", 0.008, 0.000, 0.010, 0.00, 0.24),
    ("roll", 0.012, -0.006, 0.012, 0.30, 0.06),
]


def build(link, palette, grade, layers, cam, cap, anno, seed,
          glitch=(0.04, 0.12), tail=0.70, credits=None, fixed=None):
    prev = S[-1] if S else None
    cues = [L["cue"] for L in layers if L.get("t") == "type"]
    cues.sort(key=lambda c: c["t0"])
    for i in range(len(cues) - 1):
        cues[i]["t1"] = min(cues[i]["t1"], cues[i + 1]["t0"] + 0.50)
    t1 = round(max(c["t1"] for c in cues) + tail, 3) if cues else None
    lk = None
    if prev is None or link is None:
        t0 = round(fixed[0] if fixed else cues[0]["t0"] - 1.20, 3)
    else:
        dur = float(link["dur"])
        if fixed:
            t0 = round(fixed[0], 3)
        elif not cues:
            t0 = round(prev["t1"] - dur, 3)
        else:
            tb = cues[0]["t0"]
            lo = prev["_cue_end"] - dur
            hi = tb + 0.15 - dur
            want = tb - dur - 0.25
            t0 = round((lo + hi) * 0.5 if lo > hi else min(max(want, lo), hi), 3)
        lk = dict(dur=dur, out=link["out"], prev=len(S) - 1,
                  za=float(link.get("za", 1.0)), zb=float(link.get("zb", 1.0)),
                  ra=float(link.get("ra", 0.0)), rb=float(link.get("rb", 0.0)))
        prev["t1"] = round(t0 + dur, 3)
        prev["cam"]["dur"] = round(prev["t1"] - prev["t0"], 3)
    if t1 is None:
        t1 = round(fixed[1] if fixed else t0 + 6.0, 3)
    cam["dur"] = round(t1 - t0, 3)
    nd = []
    base = (int(round(t0 * 7)) + int(seed)) % len(MICRO)
    for i, c in enumerate(cues):
        at = max(round(c["t0"] - t0, 3), 0.60)
        # 微场景：每句换一种镜头小动作（推 / 拉 / 横移 / 升降 / 移焦 / 甩滚），
        # 句首做满、0.62 s 后回不到一半，读作同一镜里的两次呼吸
        _, dx, dy, dz, dr, df = MICRO[(base + i) % len(MICRO)]
        nd.append(dict(t=at, w=0.34, dx=dx, dy=dy, dz=dz, dr=dr, df=df))
        nd.append(dict(t=round(at + 0.62, 3), w=0.26, dx=-dx * 0.42, dy=-dy * 0.42,
                       dz=-dz * 0.42, dr=-dr * 0.42, df=-df * 0.42))
    cam["nudges"] = nd
    d = dict(t0=t0, t1=t1, xfade=0.0, seed=seed, palette=palette,
             glitch=list(glitch), grade=grade, cam=cam, link=lk, tr_in=None,
             caption=cap, anno=anno, layers=layers,
             _cue_end=round(max(c["t1"] for c in cues), 3) if cues else round(t1, 3))
    if credits:
        d["credits"] = credits
    return d


def add(link, *a, **kw):
    S.append(build(link, *a, **kw))


# ================================================================ 01-08
add(dict(out="left", dur=0.55, za=1.20, ra=-3), "sepia", WARM,
    [BG("cave", fit=1.05),
     FX("sparks", z=0.46, count=70, alpha=0.9, rise=0.5, seed=71),
     TY(cue("有人用理念构筑", dy=0.02, erase=True)),
     TY(cue("名为本体的神话", dy=0.02, erase=True)),
     FIG("fig_plato", 0.855, 0.55, h=0.74, front=True, tin=19.6, tout=23.4, alpha=0.92)],
    CAM(x0=-0.014, x1=0.010, y0=0.002, y1=0.010, z0=0.0, z1=0.058, r0=-0.04, r1=0.20,
        f0=0.55, seed=3, aperture=2.0, max_blur=4),
    dict(no="PLATE 01", txt="洞穴 · 火与影", yr="前 4 世纪"),
    dict(t="理念", latin="EIDOS"), seed=11)

add(dict(out="up", dur=0.50, za=1.10, ra=4), "steel", COLD,
    [BG("academy", fit=1.06, palette="steel"),
     FX("dust", z=0.56, count=110, alpha=0.42, speed=0.03, seed=72),
     TY(cue("逻各斯随波流转", dy=0.10, erase=True)),
     TY(cue("直至阿卡德米亚", dy=0.10, erase=True))],
    CAM(x0=0.014, x1=-0.020, y0=0.014, y1=0.010, z0=0.030, z1=-0.006, r0=0.16, r1=-0.18,
        f0=0.42, seed=5, aperture=1.8, max_blur=4),
    dict(no="PLATE 02", txt="学园 · 柱廊", yr="前 387"),
    dict(t="逻各斯", latin="LOGOS"), seed=13)

add(dict(out="dl", dur=0.55, za=1.14, ra=-3), "cold",
    dict(key=(255, 150, 96), amount=0.26, contrast=1.02, lift=0.05),
    [BG("cave", idx=1, fit=1.10, palette="cold", alpha=0.52),
     FX("dust", z=0.50, count=90, alpha=0.30, speed=0.016, seed=73),
     PR("bound_figure", 0.50, 0.58, h=0.64, z=0.34),
     TY(cue("洞穴里有人囚禁", dy=0.20, erase=True)),
     TY(cue("有人指认出虚华", dy=0.20, erase=True))],
    CAM(x0=0.0, x1=0.006, y0=0.0, y1=0.004, z0=0.004, z1=0.018, f0=0.34, seed=7,
        handheld=0.7, aperture=1.4, max_blur=3),
    dict(no="PLATE 03", txt="洞喻 · 被缚者", yr="前 4 世纪"),
    dict(t="囚禁", latin="SPELUNCA"), seed=17)

add(dict(out="down", dur=0.46, za=1.08), "sepia", WARM,
    [BG("hemlock", fit=1.04),
     PR("hand_cup", 0.68, 0.60, h=0.72, z=0.30),
     FX("smoke", z=0.42, count=6, alpha=0.16, seed=74),
     TY(cue("也有人饮下毒鸩", dy=0.06, erase=True)),
     TY(cue("将死生从容作答", dy=0.06, erase=True)),
     FIG("fig_socrates", 0.20, 0.50, h=0.66, front=True, tin=32.4, tout=35.4, alpha=0.90)],
    CAM(x0=-0.004, x1=0.006, z0=0.0, z1=0.030, f0=0.30, seed=11, handheld=0.4,
        aperture=0.0, max_blur=0),
    dict(no="PLATE 04", txt="毒芹之杯", yr="前 399"),
    dict(t="毒鸩", latin="PHARMAKON"), seed=23)

add(dict(out="right", dur=0.52, za=1.0, zb=1.14), "gold", GOLD,
    [BG("celestial", fit=1.05, palette="gold"),
     FX("dust", z=0.54, count=130, alpha=0.40, speed=0.028, seed=75),
     TY(cue("神谕中有座天城", kind="line", layout="up_center", px=116, vertical=True,
            dy=-0.04, erase=True)),
     TY(cue("托名唤作耶和华", dy=0.20, erase=True))],
    CAM(x0=0.0, x1=0.012, y0=0.030, y1=-0.032, z0=0.018, z1=0.056, r0=0.0, r1=0.18,
        f0=0.55, seed=13, aperture=1.6, max_blur=4),
    dict(no="PLATE 05", txt="上帝之城", yr="426"),
    dict(t="天城", latin="CIVITAS DEI"), seed=29)

add(dict(out="ul", dur=0.55, za=1.16, ra=-6, rb=6), "gold", GOLD,
    [BG("scriptorium", fit=1.05, palette="gold"),
     FX("paper", z=0.46, count=7, alpha=0.55, seed=76),
     PR("scholar_desk", 0.44, 0.52, h=0.86, z=0.34),
     TY(cue("有位手持信理的", dy=0.18, erase=True)),
     TY(cue("托马斯意气风发", dy=-0.14, erase=True)),
     FIG("fig_aquinas", 0.83, 0.50, h=0.70, front=True, tin=40.2, tout=43.4, alpha=0.90)],
    CAM(x0=0.0, x1=0.014, y1=-0.012, z0=0.0, z1=0.072, r0=0.0, r1=0.20, f0=0.34, f1=0.72,
        seed=15, aperture=2.6, max_blur=6),
    dict(no="PLATE 06", txt="抄经院", yr="13 世纪"),
    dict(t="信理", latin="DOGMA"), seed=31)

add(dict(out="left", dur=0.50, za=1.26, ra=3), "gold", GOLD,
    [BG("disputation", fit=1.05, palette="gold"),
     dict(t="fx", mode="shaft", z=0.60, angle=-18, center=0.4, amt=0.30, drift=0.10, u_in=0.0),
     FIG("fig_plato", 0.22, 0.50, h=0.44, z=0.30, tin=44.0, tout=47.2, alpha=0.80),
     FIG("fig_kant", 0.78, 0.48, h=0.40, z=0.40, tin=44.3, tout=47.2, alpha=0.72),
     TY(cue("唯名与唯实交锋", kind="collide", dy=0.08, erase=True)),
     TY(cue("将思辨翻覆揉轧", kind="shuffle", dy=0.08, erase=True))],
    CAM(x0=-0.038, x1=0.038, z0=0.004, z1=0.018, r0=-0.14, r1=0.14, f0=0.55, seed=17,
        handheld=0.9, aperture=0.0, max_blur=0),
    dict(no="PLATE 07", txt="共相之争", yr="12 世纪"),
    dict(t="唯名", latin="NOMEN"), seed=37)

add(dict(out="dr", dur=0.55, za=1.12, ra=-4), "gold", GOLD,
    [BG("rose", fit=1.04, palette="gold"),
     FX("dust", z=0.52, count=120, alpha=0.40, speed=0.024, seed=77),
     TEX("scanline", z=0.28, alpha=0.55, speed=0.8, width=0.0016),
     TY(cue("辩驳里有谁将信仰", kind="line", layout="right_v", px=116, vertical=True,
            erase=True)),
     TY(cue("用理性来传达", dy=0.18, erase=True))],
    CAM(x0=0.0, x1=0.010, y1=0.008, z0=0.018, z1=0.054, r0=0.0, r1=0.14, f0=0.55,
        seed=19, aperture=1.8, max_blur=4),
    dict(no="PLATE 08", txt="玫瑰窗", yr="13 世纪"),
    dict(t="信仰", latin="FIDES"), seed=41)

# ================================================================ 09 蒙昧 · 神座
add(dict(out="left", dur=0.55, za=1.18, ra=-3), "sepia", ASH,
    [BG("idol", fit=1.04),
     FX("dust", z=0.54, count=110, alpha=0.38, seed=81),
     PR("bust_a", 0.82, 0.52, h=0.94, z=0.24, tilt=-5, alpha=0.95, front=True),
     TY(cue("神座在蒙昧后", dy=-0.10, erase=True)),
     TY(cue("渐渐崩塌", dy=0.18, erase=True))],
    CAM(x0=-0.010, x1=0.008, z0=0.0, z1=0.096, r0=-0.12, r1=0.10, f0=0.62, f1=0.34,
        seed=21),
    dict(no="PLATE 09", txt="蒙昧 · 神座", yr="17 世纪"),
    dict(t="蒙昧", latin="IGNORANTIA"), seed=51)

# ================================================================ 10 怀疑
add(dict(out="up", dur=0.52, za=1.12, ra=4), "steel", COLD,
    [BG("doubt", fit=1.06, palette="steel"),
     FX("dust", z=0.56, count=90, alpha=0.34, seed=82),
     FIG("fig_descartes", 0.86, 0.46, h=0.88, z=0.22, alpha=0.96),
     TY(cue("怀疑将虚妄的幻象", dy=0.04, erase=True)),
     TY(cue("拆下", kind="cut", dy=0.22, erase=True))],
    CAM(x0=0.012, x1=-0.006, z0=0.088, z1=0.004, r0=0.16, r1=-0.06, f0=0.34, f1=0.58,
        seed=23),
    dict(no="PLATE 10", txt="怀疑 · 拆解", yr="1641"),
    dict(t="怀疑", latin="DUBITATIO"), seed=53)

# ================================================================ 11 机械之眼
add(dict(out="dl", dur=0.55, za=1.20, ra=3), "sepia", WARM,
    [BG("lens", fit=1.05),
     FX("sparks", z=0.46, count=80, alpha=0.80, rise=0.4, seed=83),
     TY(cue("机械的眼把万物", dy=-0.06, erase=True)),
     TY(cue("剖析再刻画", dy=0.20, erase=True))],
    CAM(x0=0.0, x1=-0.012, y1=0.010, z0=0.0, z1=0.104, r0=0.0, r1=-0.18, f0=0.30, f1=0.66,
        seed=25, aperture=2.2),
    dict(no="PLATE 11", txt="机械之眼", yr="1665"),
    dict(t="解剖", latin="ANATOMIA"), seed=57)

# ================================================================ 12 泛神
add(dict(out="right", dur=0.55, za=1.0, zb=1.12), "cold", COLD,
    [BG("stars", fit=1.05, palette="cold"),
     FX("dust", z=0.58, count=150, alpha=0.44, speed=0.02, seed=84),
     FIG("fig_spinoza", 0.16, 0.46, h=0.84, z=0.22, alpha=0.94),
     TY(cue("勾勒出泛神实体", dy=-0.12, erase=True)),
     TY(cue("惹世人皆惊诧", dy=0.18, erase=True))],
    CAM(z0=0.096, z1=0.006, r0=0.10, r1=-0.08, f0=0.55, f1=0.86, seed=27),
    dict(no="PLATE 12", txt="泛神 · 实体", yr="1677"),
    dict(t="实体", latin="SUBSTANTIA"), seed=59)

# ================================================================ 13 白板
add(dict(out="down", dur=0.50, za=1.14), "sepia", ASH,
    [BG("slate", fit=1.05),
     FX("dust", z=0.52, count=80, alpha=0.30, size=1.4, seed=85),
     PR("scholar_desk", 0.80, 0.52, h=0.98, z=0.28, front=True, alpha=0.95),
     FIG("fig_locke", 0.14, 0.44, h=0.74, z=0.24, alpha=0.90),
     TY(cue("于是有人用白板", dy=-0.08, erase=True)),
     TY(cue("记录属于知的萌芽", dy=0.18, erase=True))],
    CAM(x0=-0.008, x1=0.012, z0=0.0, z1=0.092, r0=-0.10, r1=0.14, f0=0.30, f1=0.58, seed=29),
    dict(no="PLATE 13", txt="白板 · 经验", yr="1690"),
    dict(t="白板", latin="TABULA RASA"), seed=61)

# ================================================================ 14 因果
add(dict(out="left", dur=0.55, za=1.16, ra=-3), "steel", COLD,
    [BG("clockwork", fit=1.04, palette="steel"),
     FX("sparks", z=0.48, count=60, alpha=0.70, rise=0.3, seed=86),
     FIG("fig_hume", 0.86, 0.48, h=0.86, z=0.22, alpha=0.95),
     TY(cue("有人把怀疑探遍", dy=-0.08, erase=True)),
     TY(cue("只为勘破因果的虚假", dy=0.18, erase=True))],
    CAM(x0=0.0, x1=-0.010, z0=0.006, z1=0.094, r0=0.0, r1=-0.16, f0=0.66, f1=0.32,
        seed=31, aperture=2.4),
    dict(no="PLATE 14", txt="因果 · 探遍", yr="1739"),
    dict(t="因果", latin="CAUSA"), seed=63)

# ================================================================ 15 先验
add(dict(out="up", dur=0.52, za=1.12, ra=-5), "gold", GOLD,
    [BG("dawn", fit=1.05, palette="gold"),
     dict(t="fx", mode="shaft", z=0.62, angle=-24, center=0.36, amt=0.34, drift=0.14, u_in=0.0),
     FIG("fig_kant", 0.84, 0.50, h=0.84, z=0.24, front=True, alpha=0.94),
     TY(cue("批判在沉睡后绝醒", dy=-0.10, erase=True)),
     TY(cue("立定先验伴时空刻划", dy=0.18, erase=True))],
    CAM(x0=-0.012, x1=0.010, y0=0.008, y1=-0.010, z0=0.0, z1=0.090, r0=-0.20, r1=0.12,
        f0=0.40, f1=0.64, seed=33),
    dict(no="PLATE 15", txt="先验 · 时空", yr="1781"),
    dict(t="先验", latin="A PRIORI"), seed=67)

# ================================================================ 16 绝对精神
add(dict(out="dr", dur=0.55, za=1.22, ra=4), "gold", GOLD,
    [BG("pyramid", fit=1.04, palette="gold"),
     FX("dust", z=0.54, count=120, alpha=0.38, seed=87),
     TY(cue("在普遍理性中通向", dy=-0.12, erase=True)),
     TY(cue("那名为绝对精神的终点啊", dy=0.16, erase=True, cap=6.2))],
    CAM(x0=-0.010, x1=0.012, z0=0.0, z1=0.108, r0=-0.12, r1=0.16, f0=0.70, f1=0.30,
        seed=35, aperture=2.0),
    dict(no="PLATE 16", txt="绝对精神", yr="1807"),
    dict(t="绝对", latin="ABSOLUTUM"), seed=69)

# ================================================================ 17 间奏 · 署名
add(dict(out="ul", dur=0.60, za=1.10, ra=-4), "cold", COLD,
    [BG("celestial", fit=1.06, palette="cold", alpha=0.72),
     FX("dust", z=0.58, count=140, alpha=0.30, speed=0.016, seed=88),
     TEX("scanline", z=0.26, alpha=0.40, speed=0.5, width=0.0012),
     TY(dict(kind="credits", text="credits", t0=91.80, t1=106.20, words=[],
             seed=1701, alpha=1.0, step=1.55, y=0.315, gap=0.062,
             px_role=27, px_name=42, x_role=0.412, x_name=0.434, latin="CREDITS",
             rows=[("文案", "Gemini 3.7 Flash"), ("素材", "GPT-image 2.5"),
                   ("剪辑", "DeepSeek-V4.1f-1017"), ("歌唱", "Suno V6"),
                   ("美术指导", "GPT Astra"), ("Agent", "Deepseek Harness"),
                   ("策划人", "扎姆"), ("参考", "过期童话")]))],
    CAM(x0=0.006, x1=-0.008, y0=-0.004, y1=0.006, z0=0.020, z1=0.078, r0=0.06, r1=-0.10,
        f0=0.55, f1=0.78, seed=37, handheld=0.8, aperture=1.4, max_blur=3),
    dict(no="PLATE 17", txt="间奏 · 思辨", yr="19 世纪"),
    dict(t="思辨", latin="SPECULATIO"), seed=71, glitch=(0.02, 0.06),
    fixed=(90.35, 108.53))

# ================================================================ 18 唯心体系
add(dict(out="left", dur=0.55, za=1.0, zb=1.16), "sepia", WARM,
    [BG("pyramid", idx=1, fit=1.06),
     FX("dust", z=0.52, count=100, alpha=0.34, seed=89),
     FIG("fig_hegel", 0.84, 0.46, h=0.90, z=0.22, alpha=0.96),
     TY(cue("绝对唯心的体系", dy=-0.10, erase=True)),
     TY(cue("耸立在金字塔", dy=0.18, erase=True))],
    CAM(x0=0.0, x1=-0.014, z0=0.104, z1=0.004, r0=0.14, r1=-0.10, f0=0.34, f1=0.66, seed=39),
    dict(no="PLATE 18", txt="唯心 · 体系", yr="1817"),
    dict(t="体系", latin="SYSTEMA"), seed=73)

# ================================================================ 19 异化
add(dict(out="up", dur=0.50, za=1.20, ra=3), "sepia", ASH,
    [BG("clockwork", idx=1, fit=1.05),
     FX("sparks", z=0.46, count=90, alpha=0.85, rise=0.4, seed=90),
     TY(cue("暗藏着自我异化", dy=-0.08, erase=True)),
     TY(cue("扬弃重构的代码", dy=0.20, erase=True))],
    CAM(x0=-0.010, x1=0.008, z0=0.0, z1=0.100, r0=-0.14, r1=0.10, f0=0.62, f1=0.30,
        seed=41, aperture=2.2),
    dict(no="PLATE 19", txt="异化 · 扬弃", yr="1844"),
    dict(t="异化", latin="ENTFREMDUNG"), seed=79)

# ================================================================ 20 宗教批判
add(dict(out="right", dur=0.52, za=1.14, ra=-4, zb=1.10), "gold", GOLD,
    [BG("rose", idx=1, fit=1.06, palette="gold"),
     FX("smoke", z=0.50, count=7, alpha=0.22, seed=91),
     FIG("fig_marx", 0.175, 0.47, h=0.98, z=0.21, alpha=0.96),
     FIG("flag_red_soft", 0.885, 0.38, h=0.60, z=0.36, tilt=-9,
         raw_colour=True, alpha=0.86, seed=31),
     TY(cue("批判宗教的先驱", dy=-0.10, erase=True, kind="strike")),
     TY(cue("将迷雾荡涤振刷", dy=0.18, erase=True))],
    CAM(x0=0.010, x1=-0.012, y0=0.006, y1=-0.008, z0=0.006, z1=0.096, r0=0.10, r1=-0.16,
        f0=0.44, f1=0.70, seed=43),
    dict(no="PLATE 20", txt="批判 · 宗教", yr="1841"),
    dict(t="批判", latin="KRITIK"), seed=83)

# ================================================================ 21 实践
add(dict(out="left", dur=0.55, za=1.18, ra=3), "sepia", WARM,
    [BG("forge", fit=1.05),
     FX("sparks", z=0.50, count=110, alpha=0.95, rise=0.6, seed=92),
     FIG("fig_marx", 0.855, 0.46, h=0.92, z=0.22, alpha=0.95),
     FIG("flag_red_soft", 0.115, 0.38, h=0.54, z=0.36, tilt=10, flip=True,
         raw_colour=True, alpha=0.84, seed=32),
     TY(cue("写下实践的新章", dy=-0.10, erase=True)),
     TY(cue("待批判者再出发", dy=0.18, erase=True))],
    CAM(x0=-0.012, x1=0.010, z0=0.0, z1=0.102, r0=-0.16, r1=0.12, f0=0.66, f1=0.32, seed=45),
    dict(no="PLATE 21", txt="实践 · 新章", yr="1845"),
    dict(t="实践", latin="PRAXIS"), seed=89)

# ================================================================ 22 盲目意志
add(dict(out="dl", dur=0.55, za=1.0, zb=1.12), "cold", COLD,
    [BG("abyss", fit=1.05, palette="cold"),
     FX("smoke", z=0.52, count=6, alpha=0.20, seed=93),
     FIG("fig_schopenhauer", 0.84, 0.46, h=0.90, z=0.22, alpha=0.95),
     TY(cue("是谁说盲目意志", dy=-0.10, erase=True)),
     TY(cue("皆系于欲望惩罚", dy=0.18, erase=True))],
    CAM(x0=0.008, x1=-0.010, z0=0.100, z1=0.004, r0=0.12, r1=-0.12, f0=0.34, f1=0.72, seed=47),
    dict(no="PLATE 22", txt="意志 · 盲动", yr="1819"),
    dict(t="意志", latin="VOLUNTAS"), seed=97)

# ================================================================ 23 上帝已死
add(dict(out="up", dur=0.52, za=1.16, ra=-5, rb=5), "gold", GOLD,
    [BG("dawn", idx=1, fit=1.06, palette="gold"),
     dict(t="fx", mode="shaft", z=0.62, angle=-14, center=0.52, amt=0.30, drift=0.12, u_in=0.0),
     FIG("fig_nietzsche", 0.84, 0.44, h=0.94, z=0.21, alpha=0.96),
     TY(cue("又是谁宣布上帝已死", dy=-0.12, erase=True)),
     TY(cue("高歌超人的神话", dy=0.18, erase=True))],
    CAM(x0=-0.010, x1=0.010, y0=-0.006, y1=0.010, z0=0.0, z1=0.098, r0=-0.10, r1=0.18,
        f0=0.70, f1=0.34, seed=49),
    dict(no="PLATE 23", txt="超人 · 神话", yr="1883"),
    dict(t="超人", latin="UEBERMENSCH"), seed=101)

# ================================================================ 24 商品拜物
add(dict(out="left", dur=0.50, za=1.14, ra=3), "sepia", ASH,
    [BG("commodity", fit=1.04),
     FX("dust", z=0.54, count=100, alpha=0.34, seed=94),
     TY(cue("工业与商品拜物", dy=-0.08, erase=True)),
     TY(cue("将一切分割物化", dy=0.20, erase=True))],
    CAM(x0=-0.008, x1=0.010, z0=0.004, z1=0.092, r0=-0.10, r1=0.14, f0=0.58, f1=0.30, seed=51),
    dict(no="PLATE 24", txt="拜物 · 物化", yr="1867"),
    dict(t="拜物", latin="FETISCHISMUS"), seed=103)

# ================================================================ 25 此在（长镜，含间奏）
add(dict(out="right", dur=0.55, za=1.0, zb=1.14), "cold", COLD,
    [BG("forest", fit=1.06, palette="cold"),
     FX("dust", z=0.56, count=120, alpha=0.30, speed=0.014, seed=95),
     FIG("fig_heidegger", 0.16, 0.46, h=0.86, z=0.22, alpha=0.94),
     TY(cue("此在世界随生存的时间", dy=-0.10, erase=True)),
     TY(cue("切分后升华", dy=0.20, erase=True))],
    CAM(x0=0.010, x1=-0.014, z0=0.106, z1=0.0, r0=0.14, r1=-0.14, f0=0.34, f1=0.78,
        seed=53, handheld=0.7, aperture=1.4, max_blur=3.5),
    dict(no="PLATE 25", txt="此在 · 时间", yr="1927"),
    dict(t="此在", latin="DASEIN"), seed=107)

# ================================================================ 26 逻辑图画
add(dict(out="up", dur=0.55, za=1.20, ra=-4), "gold", GOLD,
    [BG("academy", idx=1, fit=1.05, palette="gold"),
     dict(t="fx", mode="shaft", z=0.60, angle=-20, center=0.42, amt=0.28, drift=0.10, u_in=0.0),
     PR("ladder", 0.74, 0.60, h=0.66, z=0.30, tilt=-4, alpha=0.66),
     TY(cue("逻辑厘清着世界的图画", dy=-0.02, erase=True, cap=8.2))],
    CAM(x0=-0.010, x1=0.012, z0=0.0, z1=0.104, r0=-0.12, r1=0.14, f0=0.66, f1=0.30,
        seed=55, aperture=2.0),
    dict(no="PLATE 26", txt="逻辑 · 图画", yr="1921"),
    dict(t="逻辑", latin="LOGICA"), seed=109)

# ================================================================ 27 沉默的断崖
add(dict(out="dl", dur=0.55, za=1.0, zb=1.12), "steel", COLD,
    [BG("abyss", idx=1, fit=1.06, palette="steel"),
     FX("dust", z=0.58, count=90, alpha=0.26, seed=96),
     TY(cue("也守望沉默无言的断崖", dy=0.10, erase=True, cap=8.2))],
    CAM(x0=0.012, x1=-0.012, z0=0.098, z1=0.0, r0=0.10, r1=-0.10, f0=0.40, f1=0.84,
        seed=57, handheld=0.6),
    dict(no="PLATE 27", txt="沉默 · 断崖", yr="1921"),
    dict(t="沉默", latin="SILENTIUM"), seed=113)

# ================================================================ 28 现象
add(dict(out="left", dur=0.55, za=1.16, ra=4), "gold", GOLD,
    [BG("forest", idx=1, fit=1.05, palette="gold"),
     FX("dust", z=0.54, count=110, alpha=0.34, seed=97),
     FIG("fig_husserl", 0.16, 0.46, h=0.86, z=0.22, alpha=0.94),
     TY(cue("直面事物本身 在现象里发芽", dy=0.06, erase=True, cap=8.4))],
    CAM(x0=-0.010, x1=0.010, z0=0.0, z1=0.100, r0=-0.12, r1=0.14, f0=0.34, f1=0.70, seed=59),
    dict(no="PLATE 28", txt="现象 · 事物本身", yr="1913"),
    dict(t="现象", latin="PHAENOMENON"), seed=127)

# ================================================================ 29 不可说
add(dict(out="up", dur=0.55, za=1.10, ra=-3), "cold", COLD,
    [BG("abyss", idx=2, fit=1.08, palette="cold", alpha=0.34),
     FX("dust", z=0.60, count=50, alpha=0.22, seed=98),
     FIG("fig_wittgenstein", 0.84, 0.46, h=0.92, z=0.22, alpha=0.96),
     TY(cue("凡不可说的 当保持沉默", kind="line", layout="up_center", px=110,
            vertical=True, dy=-0.02, erase=True, cap=8.2))],
    CAM(x0=0.0, x1=0.006, z0=0.010, z1=0.062, r0=0.0, r1=-0.08, f0=0.55, f1=0.42,
        seed=61, handheld=0.5, aperture=1.2, max_blur=3),
    dict(no="PLATE 29", txt="不可说 · 沉默", yr="1922"),
    dict(t="界限", latin="LIMES"), seed=131)

# ================================================================ 30 规训
add(dict(out="left", dur=0.52, za=1.18, ra=3), "steel", COLD,
    [BG("panopticon_hall", fit=1.04, palette="steel"),
     FX("dust", z=0.56, count=100, alpha=0.32, seed=99),
     PR("eye_surveil", 0.50, 0.28, h=0.66, z=0.34, alpha=0.95),
     FIG("fig_foucault", 0.84, 0.72, h=0.74, z=0.22, alpha=0.96),
     TY(cue("有人说那微观权力", dy=-0.10, erase=True)),
     TY(cue("潜藏在规训的种种技法", dy=0.18, erase=True))],
    CAM(x0=-0.010, x1=0.008, z0=0.0, z1=0.098, r0=-0.10, r1=0.12, f0=0.64, f1=0.32,
        seed=63, aperture=2.2),
    dict(no="PLATE 30", txt="权力 · 规训", yr="1975"),
    dict(t="权力", latin="POTESTAS"), seed=137)

# ================================================================ 31 技术理性：3D 眼镜的观众
add(dict(out="left", dur=0.36, za=1.34, ra=-5), "sepia", ASH,
    [BG("crowd_glasses", fit=1.06),
     FX("dust", z=0.54, count=80, alpha=0.26, seed=100),
     TY(cue("也有人批判技术理性", dy=-0.10, erase=True))],
    CAM(x0=0.010, x1=-0.014, z0=0.0, z1=0.112, r0=0.10, r1=-0.16, f0=0.30, f1=0.70, seed=65),
    dict(no="PLATE 31", txt="技术理性 · 同质", yr="1964"),
    dict(t="技术理性", latin="RATIO INSTRUMENTALIS"), seed=139)

# ================================================================ 31b 单向度：一模一样的人头在流水线上
add(dict(out="up", dur=0.42, za=1.26, ra=4), "sepia", ASH,
    [BG("mass_line", fit=1.05),
     FX("smoke", z=0.54, count=8, alpha=0.22, seed=100),
     FIG("fig_marcuse", 0.14, 0.44, h=0.80, z=0.22, alpha=0.92),
     TY(cue("异化下的单向度化", dy=0.16, erase=True))],
    CAM(x0=0.012, x1=-0.012, z0=0.096, z1=0.0, r0=0.14, r1=-0.10, f0=0.32, f1=0.74, seed=66),
    dict(no="PLATE 32", txt="单向度 · 流水线", yr="1964"),
    dict(t="单向度", latin="HOMO UNIUS DIMENSIONIS"), seed=140)

# ================================================================ 32 形而上大厦
add(dict(out="dl", dur=0.55, za=1.22, ra=-6, rb=6), "gold", GOLD,
    [BG("ladder", fit=1.05, palette="gold"),
     FX("dust", z=0.52, count=110, alpha=0.36, seed=101),
     TY(cue("形而上崇高的大厦", dy=-0.10, erase=True)),
     TY(cue("随逻辑颠覆重构再崩塌", dy=0.18, erase=True))],
    CAM(x0=-0.012, x1=0.012, y0=0.008, y1=-0.012, z0=0.0, z1=0.106, r0=-0.14, r1=0.20,
        f0=0.66, f1=0.32, seed=67),
    dict(no="PLATE 33", txt="形而上 · 崩塌", yr="1967"),
    dict(t="形而上", latin="METAPHYSICA"), seed=149)

# ================================================================ 33 荒谬
add(dict(out="right", dur=0.55, za=1.0, zb=1.16), "cold", COLD,
    [BG("sisyphus", fit=1.05, palette="cold"),
     FX("dust", z=0.56, count=100, alpha=0.28, speed=0.014, seed=102),
     FIG("fig_camus", 0.84, 0.46, h=0.88, z=0.22, alpha=0.95),
     TY(cue("惟有直面荒谬决意自决的你我", dy=-0.04, erase=True, cap=6.4)),
     TY(cue("从不被虚无压垮", dy=0.20, erase=True, cap=7.0))],
    CAM(x0=0.008, x1=-0.010, z0=0.104, z1=0.0, r0=0.12, r1=-0.10, f0=0.36, f1=0.80,
        seed=69, handheld=0.7),
    dict(no="PLATE 34", txt="荒谬 · 自决", yr="1942"),
    dict(t="荒谬", latin="ABSURDUM"), seed=151)

# ================================================================ 34 童话
add(dict(out="left", dur=0.55, za=1.14, ra=3), "gold", GOLD,
    [BG("celestial", idx=1, fit=1.06, palette="gold"),
     FX("dust", z=0.56, count=130, alpha=0.34, speed=0.02, seed=103),
     TY(cue("哲学从不是什么", dy=-0.12, erase=True)),
     TY(cue("远离于尘世悬空的童话", dy=0.16, erase=True))],
    CAM(x0=-0.010, x1=0.010, z0=0.0, z1=0.094, r0=-0.10, r1=0.12, f0=0.60, f1=0.32, seed=71),
    dict(no="PLATE 35", txt="哲学 · 童话", yr=""),
    dict(t="童话", latin="FABULA"), seed=157)

# ================================================================ 35 燃尽
add(dict(out="up", dur=0.52, za=1.20, ra=-4), "sepia", WARM,
    [BG("forge", idx=1, fit=1.05),
     FX("sparks", z=0.50, count=130, alpha=1.0, rise=0.7, seed=104),
     TY(cue("无论何时总有人", dy=-0.10, erase=True)),
     TY(cue("燃尽自我追索几缕光华", dy=0.18, erase=True))],
    CAM(x0=-0.010, x1=0.012, z0=0.0, z1=0.100, r0=-0.12, r1=0.16, f0=0.64, f1=0.30,
        seed=73, aperture=2.2),
    dict(no="PLATE 36", txt="燃尽 · 追索", yr=""),
    dict(t="燃尽", latin="SACRIFICIUM"), seed=163)

# ================================================================ 36 微芒
add(dict(out="dl", dur=0.55, za=1.16, ra=3), "cold", COLD,
    [BG("stars", idx=1, fit=1.05, palette="cold"),
     FX("dust", z=0.58, count=150, alpha=0.40, speed=0.016, seed=105),
     TY(cue("思想的微芒指引着", dy=-0.10, erase=True)),
     TY(cue("永恒追问本质的步伐", dy=0.18, erase=True))],
    CAM(x0=0.0, x1=-0.010, z0=0.004, z1=0.100, r0=0.0, r1=-0.14, f0=0.34, f1=0.72, seed=75),
    dict(no="PLATE 37", txt="微芒 · 追问", yr=""),
    dict(t="追问", latin="QUAESTIO"), seed=167)

# ================================================================ 37 公理
add(dict(out="left", dur=0.55, za=1.0, zb=1.14), "sepia", WARM,
    [BG("academy", idx=2, fit=1.06),
     FX("dust", z=0.54, count=110, alpha=0.32, seed=106),
     TY(cue("化作公理守护着", dy=-0.10, erase=True)),
     TY(cue("反思着生命无数平凡的人啊", dy=0.18, erase=True, cap=6.6))],
    CAM(x0=0.010, x1=-0.012, z0=0.096, z1=0.0, r0=0.12, r1=-0.10, f0=0.30, f1=0.74, seed=77),
    dict(no="PLATE 38", txt="公理 · 平凡", yr=""),
    dict(t="公理", latin="AXIOMA"), seed=173)

# ================================================================ 38 向死而生
add(dict(out="right", dur=0.55, za=1.16, ra=-4, zb=1.10), "sepia", ASH,
    [BG("socrates", fit=1.05),
     FX("dust", z=0.54, count=90, alpha=0.30, seed=107),
     PR("hand_cup", 0.80, 0.52, h=0.82, z=0.26, front=True, alpha=0.94),
     PR("column_a", 0.14, 0.56, h=0.88, z=0.30, alpha=0.58),
     TY(cue("那是直面未知", dy=-0.10, erase=True)),
     TY(cue("向死而生", kind="stamp", dy=0.20, erase=True))],
    CAM(x0=0.010, x1=-0.010, z0=0.098, z1=0.0, r0=0.10, r1=-0.12, f0=0.34, f1=0.76, seed=79),
    dict(no="PLATE 39", txt="未知 · 向死", yr=""),
    dict(t="向死", latin="SEIN ZUM TODE"), seed=179)

# ================================================================ 39 自由
add(dict(out="up", dur=0.55, za=1.18, ra=3), "gold", GOLD,
    [BG("stars", idx=2, fit=1.05, palette="gold"),
     FX("dust", z=0.58, count=140, alpha=0.40, speed=0.018, seed=108),
     TY(cue("自由自觉的坚韧灵魂啊", dy=0.04, erase=True, cap=6.0))],
    CAM(x0=-0.010, x1=0.010, z0=0.0, z1=0.088, r0=-0.10, r1=0.12, f0=0.66, f1=0.34,
        seed=81, handheld=0.8),
    dict(no="PLATE 40", txt="自由 · 灵魂", yr=""),
    dict(t="自由", latin="LIBERTAS"), seed=181)

# ================================================================ 40 你看啊
add(dict(out="left", dur=0.55, za=1.10, ra=-3), "ivory", BONE,
    [BG("celestial", idx=0, fit=1.04, palette="ivory"),
     dict(t="fx", mode="shaft", z=0.62, angle=-12, center=0.46, amt=0.40, drift=0.16, u_in=0.0),
     TY(cue("你看啊", dy=0.10, erase=True, cap=5.0))],
    CAM(x0=0.0, x1=0.008, z0=0.010, z1=0.070, r0=0.0, r1=0.10, f0=0.55, f1=0.40,
        seed=83, handheld=0.5, aperture=1.2, max_blur=3),
    dict(no="PLATE 41", txt="看 · 光", yr=""),
    dict(t="看", latin="VIDERE"), seed=191)

# ================================================================ 41 真理之光
add(dict(out="up", dur=0.60, za=1.12, ra=2), "ivory", BONE,
    [BG("dawn", idx=0, fit=1.04, palette="ivory"),
     dict(t="fx", mode="shaft", z=0.60, angle=-10, center=0.5, amt=0.34, drift=0.12, u_in=0.0),
     FX("dust", z=0.56, count=150, alpha=0.34, speed=0.018, seed=109),
     TEX("scanline", z=0.26, front=True, alpha=0.30, speed=0.4, width=0.0010),
     TY(cue("真理之光终会抵达", dy=-0.08, erase=True, color=(30, 25, 20), glow=0.18)),
     TY(cue("请务必再追问一下", dy=0.14, erase=True, cap=4.6, color=(30, 25, 20), glow=0.18))],
    CAM(x0=-0.008, x1=0.008, z0=0.0, z1=0.086, r0=-0.08, r1=0.10, f0=0.66, f1=0.38, seed=85),
    dict(no="PLATE 42", txt="真理 · 追问", yr=""),
    dict(t="真理", latin="ALETHEIA"), seed=193)

# ================================================================ 42 片尾
S.append(dict(t0=round(S[-1]["t1"] - 0.6, 3), t1=262.80, xfade=0.0, seed=200,
              palette="ivory", glitch=[0.02, 0.05], grade=BONE,
              cam=CAM(z0=0.070, z1=0.0, f0=0.40, f1=0.70, seed=87, handheld=0.4,
                      aperture=1.0, max_blur=2.5),
              link=dict(dur=0.60, out="dr", prev=len(S) - 1, za=1.0, zb=1.0, ra=0.0, rb=0.0),
              tr_in=None, caption=None, anno=None,
              layers=[BG("dawn", idx=4, fit=1.10, palette="ivory", alpha=0.30),
                      FX("dust", z=0.58, count=60, alpha=0.18, speed=0.012, seed=110),
                      TY(dict(kind="quiet", text="永恒追问", t0=248.60, t1=260.60,
                              layout="center", px=124, words=[], glow=0.36, alpha=0.72,
                              seed=4201))],
              _cue_end=260.60, credits=None))
S[-2]["t1"] = round(S[-1]["t0"] + 0.60, 3)
S[-2]["cam"]["dur"] = round(S[-2]["t1"] - S[-2]["t0"], 3)


# ================================================================ post-pass
# 1) 更激进的相机：z 整体放大，按近层留安全余量；x/y/roll 也放大
# 2) 转场八种"口味"轮换：推着切 / 下一镜猛推进来 / 推+甩尾 / 双推 / 纯平移 /
#    推+反滚 / 推+同滚 / 双方都推 —— 同一个方向也不许用同一种力度
KZ, KX, KR = 1.45, 1.55, 1.70
NEAR = ("prop", "figure", "map")
# 换场表：每处衔接 = 方向 / 推拉 / 移焦 / 光 四分量的任意叠加
#   dir      整帧错位（A 沿 dir 出画、B 从反向入画）
#   za/zb    A 起推 / B 落定的倍数；没有 dir 时 B 以 (cx,cy) 为圆心径向揭开
#   rack     移焦像素；light = "black" | "bloom"，amt 幅度、w 宽度（高斯窄脉冲）
# 组合是常态：方向+推、方向+闪光、方向+黑场、闪光+推、黑场+拉、拉+移焦、方向+移焦……
def TR(dir=None, za=1.0, zb=1.0, cx=0.5, cy=0.5, rack=0.0,
       light=None, amt=0.0, w=0.16, ra=0.0, rb=0.0):
    return dict(dir=dir, za=za, zb=zb, cx=cx, cy=cy, rack=rack,
                light=light, amt=amt, w=w, ra=ra, rb=rb)


TRANS = [
    TR(dir="left", za=1.30, ra=-3),                                  # 01 洞穴
    TR(cx=0.50, cy=0.46, za=1.95, zb=1.55),                          # 02 学园·推进柱廊
    TR(dir="up", zb=1.15, light="black", amt=0.55, w=0.20),          # 03 洞喻·上移＋黑场
    TR(cx=0.68, cy=0.58, zb=2.30, rack=12),                          # 04 毒杯·拉远＋移焦
    TR(dir="right", light="bloom", amt=0.50, w=0.16),                # 05 天城·右移＋闪光
    TR(dir="ul", za=1.35, ra=-5),                                    # 06 抄经·斜推
    TR(rack=16),                                                     # 07 对峙·纯移焦
    TR(dir="dr", zb=1.30),                                           # 08 玫瑰窗·斜拉
    TR(cx=0.82, cy=0.42, za=2.05, zb=1.60,
       light="bloom", amt=0.32, w=0.13),                             # 09 神座·推进＋闪光
    TR(dir="left", light="black", amt=0.92, w=0.18),                 # 10 怀疑·左移＋全黑
    TR(dir="dl", za=1.40, ra=4),                                     # 11 机械之眼·斜推
    TR(cx=0.20, cy=0.46, zb=2.40),                                   # 12 泛神·拉远
    TR(dir="down", light="bloom", amt=0.42, w=0.15),                 # 13 白板·下移＋闪光
    TR(dir="left", rack=14),                                         # 14 因果·左移＋移焦
    TR(cx=0.84, cy=0.48, za=2.00, zb=1.55),                          # 15 先验·推进康德
    TR(dir="dr", za=1.50, rack=6, ra=5),                             # 16 绝对精神·斜推＋移焦
    TR(cx=0.50, cy=0.50, za=1.35, zb=1.40,
       light="bloom", amt=0.78, w=0.15),                             # 17 间奏·闪光＋推
    TR(cx=0.84, cy=0.46, zb=2.35, light="black", amt=0.50, w=0.20),  # 18 唯心·黑场＋拉
    TR(cx=0.50, cy=0.50, za=2.10, zb=1.60),                          # 19 异化·推进齿轮
    TR(dir="right", light="black", amt=0.45, w=0.20),                # 20 宗教批判·右移＋半黑
    TR(dir="left", za=1.40, ra=3),                                   # 21 实践·左推
    TR(dir="dl", light="black", amt=0.92, w=0.18),                   # 22 意志·斜移＋全黑
    TR(cx=0.84, cy=0.44, za=2.10, zb=1.60,
       light="bloom", amt=0.30, w=0.13),                             # 23 超人·推进＋闪光
    TR(dir="right", zb=1.25),                                        # 24 拜物·右拉
    TR(cx=0.16, cy=0.46, zb=2.30, rack=10),                          # 25 此在·拉远＋移焦
    TR(cx=0.74, cy=0.50, za=2.00, zb=1.55),                          # 26 逻辑·推进天梯
    TR(dir="up", zb=1.30, rack=8),                                   # 27 断崖·上拉＋移焦
    TR(dir="left", rack=16),                                         # 28 现象·左移＋移焦
    TR(light="black", amt=0.92, w=0.18, rack=12),                    # 29 不可说·黑场＋移焦
    TR(cx=0.50, cy=0.28, za=2.15, zb=1.65,
       light="bloom", amt=0.22, w=0.12),                             # 30 规训·推进那只眼＋微闪
    TR(dir="left", za=1.40),                                         # 31 技术理性·快甩推进
    TR(cx=0.62, cy=0.55, za=2.05, zb=1.58,
       light="bloom", amt=0.50, w=0.16),                             # 32 单向度·闪光＋推进流水线
    TR(dir="dl", za=1.50, rack=8, ra=-6),                            # 33 形而上·斜推＋移焦
    TR(cx=0.84, cy=0.46, zb=2.35),                                   # 34 荒谬·拉远加缪
    TR(dir="left", light="bloom", amt=0.78, w=0.15),                 # 35 童话·左移＋闪光
    TR(cx=0.50, cy=0.62, za=2.00, zb=1.55),                          # 36 燃尽·推进火星
    TR(cx=0.50, cy=0.40, zb=2.40, rack=10),                          # 37 微芒·拉远＋移焦
    TR(dir="left", rack=16),                                         # 38 公理·左移＋移焦
    TR(dir="right", zb=1.25),                                        # 39 向死·右拉
    TR(dir="up", light="black", amt=0.40, w=0.20),                   # 40 自由·上移＋半黑
    TR(cx=0.50, cy=0.50, za=1.40, zb=1.45,
       light="bloom", amt=0.78, w=0.15),                             # 41 你看啊·闪光＋推
    TR(cx=0.72, cy=0.52, za=2.05, zb=1.55,
       light="bloom", amt=0.30, w=0.13),                             # 42 真理·推进日出＋微闪
    TR(cx=0.50, cy=0.50, zb=2.20, light="bloom", amt=0.78, w=0.15),  # 43 片尾·闪光＋拉
]

li = 0
for s in shots:
    if not s.get("link"):
        continue
    s["link"].update(TRANS[li % len(TRANS)])
    li += 1

KZ, KX, KR = 1.45, 1.55, 1.70
NEAR = ("prop", "figure", "map")

# 更激进的镜内相机
for s in shots:
    if not s.get("caption"):          # 片头卡与片尾保持原有节奏，不放大
        continue
    near = [float(L.get("z", 1.0)) for L in s["layers"] if L.get("t") in NEAR]
    zcap = max(0.03, (min(near) if near else 0.9) - 0.12)
    newk = []
    for k in s["cam"]["keys"]:
        k = list(k)
        k[1] = round(k[1] * KX, 4)
        k[2] = round(k[2] * KX, 4)
        k[3] = round(min(zcap, max(0.0, k[3] * KZ)), 4)
        k[4] = round(k[4] * KR, 3)
        newk.append(tuple(k))
    s["cam"]["keys"] = newk
    ztop = max(x[3] for x in newk)
    for nd in s["cam"].get("nudges") or []:
        if nd["dz"] > 0:
            nd["dz"] = round(min(nd["dz"], max(0.004, zcap - ztop)), 4)

# 3) 画面里不再出现 PLATE 编号与拉丁小标（数据保留，供审稿与分镜表用）
for s in shots:
    s["hide_meta"] = True

# 4) 文字不得跨场景
for s in shots:
    lim = round(s["t1"] - 0.02, 3)
    for L in s["layers"]:
        c = L.get("cue")
        if c and c["t1"] > lim:
            c["t1"] = lim
        if c and c["t1"] - c["t0"] < 0.5:
            c["t1"] = c["t0"] + 0.5
    cs = [L["cue"] for L in s["layers"] if L.get("cue")]
    if cs:
        s["_cue_end"] = round(max(c["t1"] for c in cs), 3)

json.dump(shots, open(os.path.join(HERE, "shots_v15.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("shots", len(shots), "->", shots[-1]["t1"], "s")
for s in shots[10:]:
    L = s.get("link") or {}
    print("  %6.2f-%6.2f  %-13s out=%-4s dur=%-4s nudge=%d" % (
        s["t0"], s["t1"], (s.get("caption") or {}).get("no", ""), L.get("out", "-"),
        L.get("dur", "-"), len(s["cam"].get("nudges") or [])))
