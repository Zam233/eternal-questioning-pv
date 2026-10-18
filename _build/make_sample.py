# -*- coding: utf-8 -*-
"""Sample: shots 01-08 (0 - 46.5 s) built with the camera + prop + grade grammar."""
import json, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PUNCT = re.compile(r'[\s\u3000"\u201c\u201d\'\u2018\u2019,，.。!！?？;；:：、]')

rows = json.load(io.open(os.path.join(HERE, "timing_auto.json"), encoding="utf-8"))
BY = {}
for r in rows:
    BY[PUNCT.sub("", r["text"])] = r


def cue(text, layout, px, kind="line", **kw):
    key = PUNCT.sub("", text)
    r = BY.get(key)
    t0 = kw.pop("t0", None)
    t1 = kw.pop("t1", None)
    if r is None:
        if t0 is None:
            raise KeyError(key)
        words = []
        base = dict(t0=t0, t1=t1 if t1 is not None else t0 + 4.0)
    else:
        base = dict(t0=r["t0"], t1=r["t1"] + 0.30)
        words = [{"t0": w["t0"]} for w in r["words"]]
    c = dict(kind=kind, text=key, t0=base["t0"], t1=base["t1"], layout=layout, px=px,
             words=words, glow=0.55, seed=abs(hash(key)) % 9999)
    c.update(kw)
    return c


def T(c, z=0.30):
    return dict(t="type", z=z, cue=c)


WARM = dict(key=(255, 150, 92), amount=0.34, contrast=1.06, lift=-0.01)
WARM_DIM = dict(key=(240, 150, 100), amount=0.30, contrast=1.04, lift=-0.02)
COLD = dict(key=(196, 214, 238), amount=0.30, contrast=1.05, lift=0.0)
MIDD = dict(key=(232, 190, 120), amount=0.30, contrast=1.03, lift=0.01)
STEEL = dict(key=(170, 190, 215), amount=0.30, contrast=1.10, lift=-0.01)

SHOTS = [
    # ---- 01 片头
    dict(t0=0.0, t1=18.90, seed=11, palette="sepia", glitch=[0.04, 0.02],
         grade=WARM, trans_in="flash_soft",
         cam=dict(seed=3, handheld=1.0, aperture=2.6, max_blur=6,
                  keys=[(0.0, 0.000, 0.000, 0.000, 0.0, 0.62),
                        (1.0, 0.006, 0.010, 0.060, 0.20, 0.62)]),
         caption=dict(no="PLATE 01", txt="序 · 爱智", yr=""),
         anno=dict(t="追问", latin="QUAESTIO"), anno_pos="br",
         layers=[
             dict(t="bg", src="cave", idx=0, z=1.00, palette="sepia", fit=1.04),
             dict(t="prop", src="steps", z=0.22, x=0.50, y=1.02, h=0.34),
             T(cue("追问", "center", 430, kind="bleed", t0=2.2, t1=7.6), z=0.34),
         ]),
    # ---- 02
    dict(t0=18.90, t1=22.70, seed=23, palette="sepia", glitch=[0.03, 0.10],
         grade=WARM,
         cam=dict(seed=5, handheld=1.1, aperture=2.2, max_blur=5,
                  keys=[(0.0, 0.000, 0.000, 0.000, 0.0, 0.60),
                        (1.0, 0.004, -0.006, 0.070, 0.20, 0.60)]),
         caption=dict(no="PLATE 02", txt="洞穴 · 火与影", yr="前 4 世纪"),
         anno=dict(t="理念", latin="EIDOS"), anno_pos="br",
         layers=[
             dict(t="bg", src="cave", idx=0, z=1.00, palette="sepia", fit=1.06),
             dict(t="prop", src="amphora", z=0.60, x=0.255, y=0.715, h=0.40),
             T(cue("有人用理念构筑", "low_left", 190)),
             T(cue("名为本体的神话", "up_right", 180)),
         ]),
    # ---- 03 学园：右平移 + 冷光
    dict(t0=22.70, t1=26.60, seed=31, palette="steel", glitch=[0.04, 0.12],
         grade=COLD,
         cam=dict(seed=7, handheld=1.0, aperture=2.0, max_blur=5,
                  keys=[(0.0, -0.012, 0.000, 0.050, -0.20, 0.55),
                        (1.0, 0.020, 0.004, 0.000, 0.18, 0.55)]),
         caption=dict(no="PLATE 03", txt="学园 · 柱廊", yr="前 387"),
         anno=dict(t="逻各斯", latin="LOGOS"), anno_pos="bl",
         layers=[
             dict(t="bg", src="academy", idx=0, z=1.00, palette="steel", fit=1.05),
             dict(t="prop", src="torso", z=0.24, x=0.865, y=0.615, h=0.94),
             T(cue("逻各斯随波流转", "center", 200, kind="wave")),
             T(cue("直至阿卡德米亚", "up_right", 175)),
         ]),
    # ---- 04 影子戏：静机位，只有影子走
    dict(t0=26.60, t1=30.90, seed=37, palette="rust", glitch=[0.05, 0.16],
         grade=WARM,
         cam=dict(seed=9, handheld=0.6, aperture=1.8, max_blur=4,
                  keys=[(0.0, 0.000, 0.000, 0.004, 0.0, 0.55),
                        (1.0, 0.002, 0.000, 0.010, 0.10, 0.55)]),
         caption=dict(no="PLATE 04", txt="洞喻 · 被缚者", yr="前 4 世纪"),
         anno=dict(t="囚禁", latin="SPELUNCA"), anno_pos="br",
         layers=[
             dict(t="bg", src="cave", idx=1, z=1.00, palette="rust", fit=1.10),
             dict(t="prop", src="cave_shadow", z=0.34, x=0.36, y=0.55, h=0.80,
                  blend="multiply", alpha=0.85, motion_x=0.09, depth_blur=1.2),
             dict(t="prop", src="shackles", z=0.58, x=0.185, y=0.560, h=0.36),
             T(cue("洞穴里有人囚禁", "low_left", 190, kind="wave")),
             T(cue("有人指认出虚华", "up_right", 180)),
         ]),
    # ---- 05 毒杯：完全静止
    dict(t0=30.90, t1=35.00, seed=41, palette="sepia", glitch=[0.02, 0.06],
         grade=WARM_DIM,
         cam=dict(seed=11, handheld=0.4, aperture=0, max_blur=0,
                  keys=[(0.0, 0.0, 0.0, 0.0, 0.0, 0.55),
                        (1.0, 0.0, 0.0, 0.0, 0.0, 0.55)]),
         caption=dict(no="PLATE 05", txt="毒芹之杯", yr="前 399"),
         anno=dict(t="毒鸩", latin="PHARMAKON"), anno_pos="bl",
         layers=[
             dict(t="bg", src="hemlock", idx=0, z=1.00, palette="sepia", fit=1.03),
             dict(t="prop", src="cup_hemlock", z=0.24, x=0.235, y=0.640, h=0.46),
             T(cue("也有人饮下毒鸩", "low_left", 195)),
             T(cue("将死生从容作答", "center", 205, kind="punch")),
         ]),
    # ---- 06 天城：升降上升
    dict(t0=35.00, t1=38.70, seed=43, palette="gold", glitch=[0.03, 0.10],
         grade=MIDD,
         cam=dict(seed=13, handheld=0.9, aperture=2.0, max_blur=5,
                  keys=[(0.0, 0.000, 0.022, 0.020, 0.0, 0.50),
                        (1.0, 0.006, -0.030, 0.055, 0.15, 0.50)]),
         caption=dict(no="PLATE 06", txt="上帝之城", yr="426"),
         anno=dict(t="天城", latin="CIVITAS DEI"), anno_pos="bl",
         layers=[
             dict(t="bg", src="celestial", idx=0, z=1.00, palette="gold", fit=1.05),
             dict(t="prop", src="censer", z=0.58, x=0.50, y=0.285, h=0.30),
             T(cue("神谕中有座天城", "up_center", 120, vertical=True)),
             T(cue("托名唤作耶和华", "low_center", 170)),
         ]),
    # ---- 07 抄经房：推 + 焦点转移
    dict(t0=38.70, t1=42.70, seed=47, palette="gold", glitch=[0.04, 0.12],
         grade=MIDD,
         cam=dict(seed=15, handheld=1.0, aperture=3.0, max_blur=7,
                  keys=[(0.0, 0.000, 0.000, 0.000, 0.0, 0.24),
                        (0.55, 0.004, -0.004, 0.045, 0.10, 0.24),
                        (1.0, 0.010, -0.010, 0.085, 0.20, 0.80)]),
         caption=dict(no="PLATE 07", txt="抄经院", yr="13 世纪"),
         anno=dict(t="信理", latin="DOGMA"), anno_pos="bl",
         layers=[
             dict(t="bg", src="scriptorium", idx=0, z=1.00, palette="gold", fit=1.05),
             dict(t="prop", src="illum_page", z=0.52, x=0.315, y=0.560, h=0.30, tilt=6),
             dict(t="prop", src="quill", z=0.24, x=0.845, y=0.660, h=0.52),
             T(cue("有位手持信理的", "low_left", 185, kind="dossier")),
             T(cue("托马斯意气风发", "center", 200, kind="title3d")),
         ]),
    # ---- 08 对峙：无道具，纯文字对撞
    dict(t0=42.70, t1=46.50, seed=53, palette="gold", glitch=[0.05, 0.18],
         grade=MIDD,
         cam=dict(seed=17, handheld=0.7, aperture=0, max_blur=0,
                  keys=[(0.0, 0.0, 0.0, 0.005, 0.0, 0.55),
                        (1.0, 0.0, 0.0, 0.008, 0.0, 0.55)]),
         caption=dict(no="PLATE 08", txt="共相之争", yr="12 世纪"),
         anno=dict(t="唯名", latin="NOMEN"), anno_pos="br",
         layers=[
             dict(t="bg", src="disputation", idx=0, z=1.00, palette="gold", fit=1.04),
             T(cue("唯名与唯实交锋", "center", 190, kind="collide")),
             T(cue("将思辨翻覆揉轧", "center", 195, kind="skew")),
         ]),
]

json.dump(SHOTS, open(os.path.join(HERE, "shots_sample.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wrote shots_sample.json", len(SHOTS), "shots", SHOTS[-1]["t1"], "s")


