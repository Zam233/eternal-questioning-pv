# -*- coding: utf-8 -*-
"""v19 定稿：在 shots_v17 的基础上按《分镜表 v19》定稿参数。

只做四件事：
  1. 中间层瘦身到 9 个人像（其余场不加任何劣质道具）
  2. 人像 3D：yaw ±6°、透视转卡、景深；第二句被光吃掉或压暗
  3. 场域：每个双句镜在第二句翻一次（mosaic / light / ink）
  4. 文字：字号地板已在引擎里（128/116/104），不压暗带、不越界

产物 shots_v19.json（渲染用）。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "shots_v17.json")
DST = os.path.join(HERE, "shots_v19.json")

# 保留的 9 位：只在"这个人真的是这一句的主语"时出现
KEEP = {
    (18.42, "fig_plato"), (30.90, "fig_socrates"), (56.60, "fig_descartes"),
    (80.36, "fig_kant"), (107.98, "fig_hegel"), (115.47, "fig_marx"),
    (126.91, "fig_nietzsche"), (134.91, "fig_heidegger"), (175.47, "fig_foucault"),
}
# 被"光吃掉"（exp 上冲）还是被"压暗"（exp 下压）
EAT = {18.42, 56.60, 107.98, 126.91, 175.47}
DARK = {30.90, 80.36, 115.47, 134.91}

shots = json.load(io.open(SRC, encoding="utf-8"))
MODES = ["mosaic", "light", "ink"]

for s in shots:
    t0 = round(float(s["t0"]), 2)
    lay = s.get("layers") or []

    # ---- 1) 人像瘦身
    keep = []
    for L in lay:
        if L.get("t") == "figure" and L.get("src", "").startswith("fig_"):
            if (t0, L["src"]) not in KEEP:
                continue
        keep.append(L)
    s["layers"] = keep
    lay = s["layers"]

    cues = sorted([L["cue"] for L in lay if L.get("t") == "type"], key=lambda c: c["t0"])

    # ---- 2) 人像 3D + 第二句退场
    for L in lay:
        if L.get("t") != "figure" or not L.get("src", "").startswith("fig_"):
            continue
        L["yaw0"], L["yaw1"] = 6.0, -2.0
        L["pitch0"], L["pitch1"] = 0.0, 0.0
        if L.get("tin") is None and cues:
            L["tin"] = float(cues[0]["words"][0]["t0"]) - 0.35
        # 不设 tout：第二句只靠 exp 把人物"照白/压暗"，层不消失
        L.pop("tout", None)
        if t0 in EAT:
            L["exp0"], L["exp1"] = 1.0, 1.42
        elif t0 in DARK:
            L["exp0"], L["exp1"] = 1.0, 0.72
        else:
            L["exp0"], L["exp1"] = 1.0, 1.15
    # 人物在的镜：景深（人实、背景化开）
    if any(L.get("t") == "figure" and L.get("src", "").startswith("fig_") for L in lay):
        cam = s["cam"]
        cam["aperture"] = 4.2
        cam["max_blur"] = 9.0
        ks = cam["keys"]
        ks[0] = list(ks[0]); ks[-1] = list(ks[-1])
        ks[0][5] = 0.42
        ks[-1][5] = 0.58

    # ---- 3) 场域：每个双句镜第二句翻一次（已有 B 层的跳过）
    has_b = any(L.get("t") == "bg" and L.get("tin") is not None for L in lay)
    if len(cues) > 1 and not has_b:
        b0 = next((L for L in lay if L.get("t") == "bg"), None)
        if b0 is not None:
            t2 = float(cues[1]["words"][0]["t0"]) if cues[1].get("words") else cues[1]["t0"]
            lay.append(dict(t="bg", src=b0.get("src"), idx=int(b0.get("idx", 0)),
                            z=0.995, mode=MODES[int(t0) % len(MODES)],
                            palette=b0.get("palette"), fit=b0.get("fit", 1.05),
                            alpha=1.0, tin=round(t2 - 0.05, 3), dur_in=0.75, paper=False))

    # ---- 4) 后期：不再用 edge / scratch（会把字一起吃掉）
    post = s.get("post") or {}
    post.pop("edge0", None); post.pop("edge1", None); post.pop("scratch", None)
    s["post"] = post


# ---- 5) 镜 26 的"那名为 绝对精神 的终点啊"拆成上/中/下三块（参考片的三段式）
def _split_long_line(sh):
    lay = sh.get("layers") or []
    for L in lay:
        c = L.get("cue") or {}
        if not c.get("text", "").startswith("那名为绝对精神"):
            continue
        ws = c.get("words") or []
        gs = c.get("glyph") or []
        if len(ws) < 11 or len(gs) < 11:
            return
        segs = [(0, 3, "那名为", "up_center", 150, 86.14, 87.30, 0.200),
                (3, 7, "绝对精神", "center", 120, 86.88, 88.20, 0.440),
                (7, 11, "的终点啊", "low_right", 120, 87.88, 90.40, 0.780)]
        new_layers = []
        for st, en, txt, layout, px, t0, t1, ay in segs:
            c2 = dict(c)
            c2.update(kind="line", text=txt, layout=layout, px=px, t0=t0, t1=t1,
                      anchor_y=ay,
                      words=[dict(t0=float(w["t0"])) for w in ws[st:en]],
                      glyph=[dict(g) for g in gs[st:en]], segs=[])
            c2.pop("band", None)
            new_layers.append(dict(t="type", z=0.30, cue=c2))
        lay.remove(L)
        lay.extend(new_layers)
        return

for sh in shots:
    if abs(float(sh["t0"]) - 84.28) < 0.05:
        _split_long_line(sh)

json.dump(shots, io.open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
n_fig = sum(1 for s in shots for L in s.get("layers") or []
            if L.get("t") == "figure" and L.get("src", "").startswith("fig_"))
n_b = sum(1 for s in shots for L in s.get("layers") or []
          if L.get("t") == "bg" and L.get("tin") is not None)
print("figures", n_fig, "bg-flips", n_b, "->", DST)
