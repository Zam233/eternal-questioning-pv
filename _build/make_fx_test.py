# -*- coding: utf-8 -*-
"""Throwaway: prove the procedural middle layers read on top of a real shot."""
import json, io, os, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

src = json.load(io.open(os.path.join(HERE, "shots_open8.json"), encoding="utf-8"))
by = {s["caption"]["txt"]: s for s in src if s.get("caption")}

ADD = {
    "洞穴 · 火与影": dict(t="fx", mode="sparks", z=0.44, count=70, alpha=0.85, rise=0.5),
    "学园 · 柱廊": dict(t="fx", mode="dust", z=0.55, count=110, alpha=0.42, speed=0.03),
    "洞喻 · 被缚者": dict(t="fx", mode="dust", z=0.48, count=90, alpha=0.35, speed=0.02),
    "毒芹之杯": dict(t="fx", mode="smoke", z=0.40, count=10, alpha=0.30),
    "抄经院": dict(t="fx", mode="paper", z=0.42, count=7, alpha=0.55),
    "玫瑰窗": dict(t="fx", mode="dust", z=0.52, count=120, alpha=0.40, speed=0.02),
}
for k, v in ADD.items():
    s = by.get(k)
    if s:
        s["layers"].insert(1, v)

out = os.path.join(HERE, "shots_fx_test.json")
json.dump(src, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(src), "shots")
