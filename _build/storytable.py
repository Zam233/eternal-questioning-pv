# -*- coding: utf-8 -*-
"""把 shots_v15.json 里每镜的换场写成"分量叠加"的人话，重排分镜表。"""
import io
import json

DIR = {"left": "左移", "right": "右移", "up": "上移", "down": "下移",
       "ul": "左上移", "ur": "右上移", "dl": "左下移", "dr": "右下移"}


def desc(L):
    d = L.get("dir")
    za, zb = float(L.get("za", 1.0)), float(L.get("zb", 1.0))
    rack, light = float(L.get("rack", 0.0)), L.get("light")
    amt = float(L.get("amt", 0.0))
    cx, cy = float(L.get("cx", 0.5)), float(L.get("cy", 0.5))
    parts = []
    if d:
        parts.append(DIR.get(d, d))
        if za > 1.005:
            parts.append("推×%.2f" % za)
        elif zb > 1.005:
            parts.append("拉×%.2f" % zb)
    else:
        if za > 1.005:
            parts.append("推进 (%.2f,%.2f) ×%.2f" % (cx, cy, za))
        elif zb > 1.005:
            parts.append("拉远 (%.2f,%.2f) ×%.2f" % (cx, cy, zb))
    if rack > 0.5:
        parts.append("移焦%.0fpx" % rack)
    if light == "black":
        parts.append("黑场%.0f%%" % (amt * 100))
    elif light == "bloom":
        parts.append("闪光%.0f%%" % (amt * 100))
    return " ＋ ".join(parts) if parts else "叠化"


S = json.load(io.open("shots_v15.json", encoding="utf-8"))
S.sort(key=lambda x: x["t0"])
rows = []
for x in S:
    cap = x.get("caption")
    if not cap:
        continue
    cues = sorted([L["cue"] for L in x["layers"] if L.get("t") == "type"],
                  key=lambda c: c["t0"])
    txts = [("（空镜 · 署名两栏设计）" if c.get("kind") == "credits" else c["text"])
            for c in cues]
    txt = " / ".join(t for t in txts if t != "credits") or "（空镜）"
    bg = [L for L in x["layers"] if L.get("t") == "bg"]
    mids = [L["src"] for L in x["layers"] if L.get("t") in ("prop", "figure", "map")]
    L = x.get("link") or {}
    tr = "%s %.2fs" % (desc(L), L.get("dur", 0))
    ks = x["cam"]["keys"]
    k0, k1 = ks[0], ks[-1]
    dz = k1[3] - k0[3]
    cam = ("推%.2f" % dz) if dz > 0.03 else (("拉%.2f" % abs(dz)) if dz < -0.03 else "")
    dx = k1[1] - k0[1]
    if abs(dx) > 0.008:
        cam += (" · 横%+.3f" % dx)
    dr = k1[4] - k0[4]
    if abs(dr) > 0.06:
        cam += (" · 滚%+.2f" % dr)
    an = x.get("anno") or {}
    rows.append("| %s | %.1f–%.1f | %s | %s%s | %s | %s | %s |" % (
        cap["no"].replace("PLATE ", ""), x["t0"], x["t1"], txt,
        bg[0]["src"] if bg else "-",
        (" + " + "+".join(mids)) if mids else "", tr, cam,
        (an.get("t", "") + " " + an.get("latin", "")).strip()))
tbl = "\n".join(rows)
doc = io.open(r"..\PV_分镜表_v14.md", encoding="utf-8").read()
a = doc.index("| 镜 | 时间 |")
b = doc.index("## 四、")
head = ("| 镜 | 时间 | 词句 | 底板 + 中间层 | 换场（分量叠加） | 镜内相机 | 概念 |\n"
        "|---|---|---|---|---|---|---|\n")
doc = doc[:a] + head + tbl + "\n\n" + doc[b:]
io.open(r"..\PV_分镜表_v14.md", "w", encoding="utf-8").write(doc)
print("rows", len(rows))
for x in S:
    if x.get("link"):
        L = x["link"]
        print("  %6.2f  %s" % (x["t0"], desc(L)))
