# -*- coding: utf-8 -*-
"""Layered test v2: one physical camera drives background, props and type."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def cue(text, t0, t1, layout, px, kind="line", words=None, **kw):
    c = dict(kind=kind, text=text, t0=t0, t1=t1, layout=layout, px=px,
             words=words or [], glow=0.55, seed=abs(hash(text)) % 9999)
    c.update(kw)
    return c


SHOTS = [
    # ---- A  洞穴：缓慢推轨 + 轻微左移 + 0.35° 侧倾
    dict(t0=18.55, t1=23.40, seed=11, palette="sepia", glitch=[0.03, 0.10],
         caption=dict(no="PLATE 01", txt="洞穴 · 火与影", yr="前 4 世纪"),
         anno=dict(t="理念", latin="EIDOS"), anno_pos="br",
         cam=dict(seed=3, handheld=1.0, keys=[
             (0.0, 0.000, 0.000, 0.000, 0.0),
             (1.0, 0.018, 0.008, 0.070, 0.35)]),
         layers=[
             dict(t="bg", src="cave", idx=0, z=1.00, palette="sepia", fit=1.06),
             dict(t="prop", src="brazier", z=0.62, x=0.235, y=0.735, h=0.34),
             dict(t="prop", src="column_a", z=0.24, x=0.905, y=0.60, h=0.98, depth_blur=0.8),
             dict(t="type", z=0.30, cue=cue("有人用理念构筑", 18.88, 20.82, "low_left", 190)),
             dict(t="type", z=0.30, cue=cue("名为本体的神话", 20.82, 22.86, "up_right", 175)),
         ]),
    # ---- B  学园：向右横移 + 微拉回
    dict(t0=23.40, t1=27.40, seed=17, palette="gold", glitch=[0.04, 0.14],
         caption=dict(no="PLATE 02", txt="学园 · 柱廊", yr="前 387"),
         anno=dict(t="逻各斯", latin="LOGOS"), anno_pos="bl",
         cam=dict(seed=5, handheld=1.1, keys=[
             (0.0, -0.012, 0.000, 0.055, -0.25),
             (1.0, 0.022, 0.004, 0.000, 0.20)]),
         layers=[
             dict(t="bg", src="academy", idx=0, z=1.00, palette="gold", fit=1.05),
             dict(t="prop", src="bust_b", z=0.58, x=0.215, y=0.615, h=0.50),
             dict(t="prop", src="column_b", z=0.26, x=0.835, y=0.660, h=0.88, depth_blur=0.6),
             dict(t="type", z=0.31, cue=cue("逻各斯随波流转", 22.86, 24.88, "center", 200,
                                            kind="wave")),
             dict(t="type", z=0.31, cue=cue("直至阿卡德米亚", 25.18, 26.88, "up_right", 170)),
         ]),
    # ---- C  洞穴：推近 + 0.45° 侧倾
    dict(t0=27.40, t1=31.20, seed=23, palette="rust", glitch=[0.05, 0.18],
         caption=dict(no="PLATE 03", txt="洞喻 · 被缚者", yr="前 4 世纪"),
         anno=dict(t="囚禁", latin="SPELUNCA"), anno_pos="br",
         cam=dict(seed=7, handheld=1.2, keys=[
             (0.0, 0.000, 0.010, 0.000, 0.0),
             (1.0, -0.010, -0.006, 0.095, -0.45)]),
         layers=[
             dict(t="bg", src="cave", idx=0, z=1.00, palette="rust", fit=1.08),
             dict(t="prop", src="chain", z=0.60, x=0.150, y=0.815, h=0.30),
             dict(t="prop", src="stele", z=0.23, x=0.845, y=0.640, h=0.90, depth_blur=0.5),
             dict(t="type", z=0.30, cue=cue("洞穴里有人囚禁", 26.88, 28.90, "low_left", 190,
                                            kind="wave")),
             dict(t="type", z=0.30, cue=cue("有人指认出虚华", 28.90, 30.92, "up_right", 180)),
         ]),
    # ---- D  毒杯：升镜 + 推近
    dict(t0=31.20, t1=35.60, seed=29, palette="sepia", glitch=[0.06, 0.22],
         caption=dict(no="PLATE 04", txt="毒芹之杯", yr="前 399"),
         anno=dict(t="毒鸩", latin="PHARMAKON"), anno_pos="bl",
         cam=dict(seed=11, handheld=0.9, keys=[
             (0.0, 0.000, 0.022, 0.000, 0.20),
             (1.0, 0.014, -0.018, 0.080, -0.25)]),
         layers=[
             dict(t="bg", src="hemlock", idx=0, z=1.00, palette="sepia", fit=1.04),
             dict(t="prop", src="book", z=0.62, x=0.760, y=0.800, h=0.28),
             dict(t="prop", src="drapery", z=0.25, x=0.165, y=0.760, h=0.70, depth_blur=0.9),
             dict(t="type", z=0.31, cue=cue("也有人饮下毒鸩", 30.92, 32.84, "low_left", 195)),
             dict(t="type", z=0.31, cue=cue("将死生从容作答", 32.84, 35.16, "center", 205,
                                            kind="punch")),
         ]),
]

json.dump(SHOTS, open(os.path.join(HERE, "shots_layer_test.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wrote shots_layer_test.json", len(SHOTS), "shots",
      round(sum(s["t1"] - s["t0"] for s in SHOTS), 2), "s")
