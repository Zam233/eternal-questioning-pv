# -*- coding: utf-8 -*-
"""P0+P1：把《文字分镜表》的「落位」读成 layout，并给每句歌词生成一个机位状态（beat）。

产出自 shots_v15.json（make_v14 的产物）：
    shots_v17.json

流程
  1. 逐字规格（glyph/segs/slope/track/drift/sink/retreat）——沿用 v1 逻辑
  2. P0：落位 -> layout + band 档位（宽窄三档），双块句分锚点
  3. P1：每句一个 beat（pose 偏移）+ 一次 accent；删掉旧的高斯 nudge
  4. 手持噪声 1.1 -> 0.55（引擎里有门控，重构图窗口内再压到 30%）
"""
import io
import json
import os
import re
import sys
from bisect import bisect_left

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pv import typespec as TS          # noqa: E402
from pv import camera as CAM           # noqa: E402

DOC = os.path.join(os.path.dirname(HERE), "PV_文字分镜表.md")
SRC = os.path.join(HERE, "shots_v15.json")
DST = os.path.join(HERE, "shots_v17.json")
GRID_PATH = os.path.join(HERE, "beat_grid.json")

GRID = json.load(io.open(GRID_PATH, encoding="utf-8")) if os.path.exists(GRID_PATH) else None
BEATS = GRID["beats"] if GRID else []
# 八分音符网格：重音落在八分上也不算错拍
BEATS8 = sorted(BEATS + [(a + b) / 2.0 for a, b in zip(BEATS, BEATS[1:])])


def snap_beat(t_abs, tol=0.12):
    """离最近八分拍点够近才吸，避免把人声的字硬拽到错的格子上。"""
    if not BEATS8:
        return t_abs
    i = bisect_left(BEATS8, t_abs)
    cand = [BEATS8[j] for j in (i - 1, i) if 0 <= j < len(BEATS8)]
    if not cand:
        return t_abs
    best = min(cand, key=lambda b: abs(b - t_abs))
    return best if abs(best - t_abs) <= tol else t_abs

BLOCK = re.compile(
    r"\*\*(\d{2}) · ([\d.]+)–([\d.]+) · (.+?)\*\*\n"
    r"(?:.*?\n)*?"
    r"落位：(.*?)\n逐字：(.*?)\n出现：(.*?)\n为什么：(.*?)\n", re.S)
PUNCT = re.compile(r'[\s\u3000"\u201c\u201d\'\u2018\u2019,，.。!！?？;；:：、]')


def norm(s):
    return PUNCT.sub("", (s or "").strip())


text = io.open(DOC, encoding="utf-8").read()
rows = BLOCK.findall(text)
print("blocks parsed:", len(rows))
if len(rows) < 60:
    raise SystemExit("解析到的块太少，检查文档格式")


# ---------------------------------------------------------------- P0 落位 -> layout
_DIRKEYS = [
    ("左下", "low_left"), ("右下", "low_right"), ("左上", "up_left"), ("右上", "up_right"),
    ("中上", "up_center"), ("上半", "up_center"), ("上部", "up_center"), ("画面中上", "up_center"),
    ("下半", "low_center"), ("下部", "low_center"), ("底边", "low_center"), ("下缘", "low_center"),
    ("正中", "center"), ("中段", "center"), ("横贯", "center"), ("中部", "center"),
    ("偏右", "far_right"), ("右中", "far_right"), ("偏左", "far_left"), ("左中", "far_left"),
]


def layout_for(pos, first):
    p = (pos or "").replace(" ", "")
    if "竖排" in p:
        if "左" in p[:6]:
            return "left_v"
        if "接续" in p or "稍右" in p:
            return "right_v2"
        return "right_v"
    # 只看落位句的开头（方位词都写在句首；后半句常出现"向右下微降""贴右下角"之类的描述）
    head = p[:16]
    best = None
    for kw, lay in _DIRKEYS:
        i = head.find(kw)
        if i >= 0 and (best is None or i < best[0]):
            best = (i, lay)
    if best:
        return best[1]
    return "center"


BAND = {
    "center": 0.72, "up_center": 0.62, "low_center": 0.64,
    "low_left": 0.50, "low_right": 0.44, "up_left": 0.50, "up_right": 0.44,
    "far_left": 0.40, "far_right": 0.36,
    "top_left": 0.40, "bottom_right": 0.36, "bottom_left": 0.44,
    "right_v": None, "right_v2": None, "left_v": None,
}

# 8 个已做分镜的镜（18.4–52.0 s）逐句手定：落位 + 横幅 + 机位
LAYOUT_FIX = {
    "有人用理念构筑": ("low_left", 0.50),
    "名为本体的神话": ("up_center", 0.62),
    "逻各斯随波流转": ("center", 0.72),
    "直至阿卡德米亚": ("low_right", 0.40),
    "洞穴里有人囚禁": ("low_left", 0.48),
    "有人指认出虚华": ("up_center", 0.60),
    "也有人饮下毒鸩": ("center", 0.72),
    "将死生从容作答": ("low_center", 0.66),
    "神谕中有座天城": ("right_v", None),
    "托名唤作耶和华": ("right_v2", None),
    "有位手持信理的": ("up_left", 0.48),
    "托马斯意气风发": ("low_left", 0.52),
    "唯名与唯实交锋": ("center", 0.72),
    "将思辨翻覆揉轧": ("low_center", 0.64),
    "辩驳里有谁将信仰": ("center", 0.72),
    "用理性来传达": ("low_right", 0.36),
}

# 机位状态：(dx, dy, dz, droll, dfocus), in, ease, accent
BEAT_FIX = {
    "有人用理念构筑": ((+0.045, -0.008, +0.012, 0.0, 0.0), 0.46, "out", (16, 0, 0, 0, 0)),
    "名为本体的神话": ((+0.015, -0.020, -0.028, 0.0, 0.0), 0.50, "out", (0, 10, 0, 0, 0)),
    "逻各斯随波流转": ((+0.000, +0.000, +0.026, 0.0, 0.0), 0.50, "out", (0, 0, 0.004, 0, 0)),
    "直至阿卡德米亚": ((-0.050, +0.020, +0.000, 0.0, 0.0), 0.46, "out", (-14, 0, 0, 0, 0)),
    "洞穴里有人囚禁": ((-0.052, +0.004, +0.010, 0.0, 0.0), 0.46, "out", (-15, 0, 0, 0, 0)),
    "有人指认出虚华": ((+0.010, -0.030, -0.026, 0.0, 0.0), 0.50, "out", (0, 10, 0, 0, 0)),
    "也有人饮下毒鸩": ((+0.010, +0.000, +0.026, 0.0, 0.0), 0.52, "out", (0, 0, 0.005, 0, 0)),
    "将死生从容作答": ((-0.020, +0.016, -0.028, 0.0, 0.0), 0.50, "out", (0, 9, 0, 0, 0)),
    "神谕中有座天城": ((+0.040, +0.000, +0.008, 0.0, 0.0), 0.48, "out", (13, 0, 0, 0, 0)),
    "托名唤作耶和华": ((+0.008, +0.050, +0.012, 0.0, 0.0), 0.50, "out", (0, 12, 0, 0, 0)),
    "有位手持信理的": ((+0.046, -0.006, +0.010, 0.0, 0.0), 0.46, "out", (15, 0, 0, 0, 0)),
    "托马斯意气风发": ((+0.010, +0.000, +0.024, 0.0, 0.0), 0.50, "out", (0, 0, 0.005, 0, 0)),
    "唯名与唯实交锋": ((+0.000, +0.000, +0.022, 0.0, 0.0), 0.50, "out", (0, 0, 0.004, 0, 0)),
    "将思辨翻覆揉轧": ((+0.055, +0.000, +0.010, +0.8, 0.0), 0.40, "out", (18, 0, 0, 0.3, 0)),
    "辩驳里有谁将信仰": ((+0.030, +0.000, +0.012, +1.2, 0.0), 0.55, "out", (10, 0, 0, 0.25, 0)),
    "用理性来传达": ((+0.006, +0.045, +0.006, 0.0, 0.0), 0.48, "out", (0, 12, 0, 0, 0)),
}


def default_beat(layout, i):
    """默认机位序列：奇偶交替的两个极端，保证相邻机位差得出来（≥100 px）。"""
    sg = 1.0 if i % 2 == 0 else -1.0
    if layout in ("right_v", "right_v2", "left_v"):
        return (0.045 * sg, 0.0, 0.010, 0.0, 0.0), "out"
    return (0.052 * sg, 0.030 * -sg, 0.016 * sg, 0.0, 0.0), "out"


def align_glyphs(gs, text):
    """逐字规格与文本对不齐时（文档漏字）按字符序列补默认项，不硬按序号错位。"""
    chars = list(text)
    if len(gs) == len(chars):
        return gs
    import difflib
    sm = difflib.SequenceMatcher(a=[g["ch"] for g in gs], b=chars, autojunk=False)
    out = []
    blank = dict(ch="", s=1.0, dy=0.0, dx=0.0, r=0.0, a=1.0, a1=None, act=None, note="")
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.extend(gs[i1:i2])
        elif tag in ("replace", "insert"):
            for j in range(j1, j2):
                out.append(dict(blank, ch=chars[j]))
            for i in range(i1, i2):
                if i - i1 >= j2 - j1:
                    out.append(gs[i])
    return out


# ---------------------------------------------------------------- 1) 逐字规格
specs = {}
for shot, t0, t1, lyric, pos, glyph_line, appear, why in rows:
    spec = TS.spec_from_block(pos, glyph_line, appear)
    spec["shot"] = shot
    spec["pos"] = pos
    specs[norm(lyric)] = spec

shots = json.load(io.open(SRC, encoding="utf-8"))

# 22.8 s 的 iris 转场会把 B 的天空开成一个蓝色软圆；改成"推 + 左甩"，落在已有语法里
for s in shots:
    if abs(float(s["t0"]) - 22.735) < 0.02 and s.get("link"):
        s["link"].update(dir="left", out="left", za=1.45, zb=1.0, ra=-2.0,
                         cx=0.5, cy=0.5, rack=0.0)
hit, miss = 0, []
for s in shots:
    for L in s.get("layers") or []:
        c = L.get("cue")
        if not c or c.get("kind") == "credits":
            continue
        key = norm(c.get("text", ""))
        spec = specs.get(key)
        if spec is None:
            miss.append(key)
            continue
        gs = align_glyphs(spec["glyph"], norm(c.get("text", "")))
        ws = c.get("words") or []
        if ws and len(ws) == len(gs):
            i = 0
            while i < len(gs):
                if gs[i]["s"] >= 1.8:
                    j = i
                    while j + 1 < len(gs) and gs[j + 1]["s"] >= 1.8:
                        j += 1
                    if j > i:
                        for k in range(i, j + 1):
                            gs[k]["at"] = float(ws[i]["t0"])
                    i = j + 1
                else:
                    i += 1
        low_txt = spec.get("appear", "") + spec.get("pos", "")
        if "底边" in low_txt or "下缘" in low_txt:
            for g in gs:
                if g["s"] < 0.8:
                    g["dy"] = float(g["dy"]) + 52.0
        if ("砸" in low_txt) or ("印" in low_txt):
            for gg in gs:
                if gg["s"] >= 1.8 and not gg.get("act"):
                    gg["act"] = "stamp" if "印" in low_txt else "slam"
        c["glyph"] = gs
        c["segs"] = spec["segs"]
        c["slope"] = spec["slope"]
        if spec["track"] is not None:
            c["track_em"] = spec["track"]
        if spec["drift"]:
            c["drift"] = spec["drift"]
        if spec["sink"]:
            c["sink"] = spec["sink"]
        if spec["retreat"]:
            c["retreat"] = True
        c["stagger"] = 0.0
        hit += 1

        # ---- P0：落位 -> layout / band / 竖排
        fix = LAYOUT_FIX.get(key)
        if fix:
            lay, band = fix
        else:
            lay = layout_for(spec.get("pos", ""), True)
            band = BAND.get(lay, 0.72)
            if "小字" in (spec.get("pos", "") + spec.get("appear", "")):
                band = round(max(0.30, (band or 0.6) * 0.82), 2)
        c["layout"] = lay
        if band:
            c["band"] = band
        c["dy"] = 0.0          # 落位已由 layout 承担，旧的整句下移作废
        c.pop("anchor_y", None)
        c.pop("vertical", None)
        if "竖排" in (spec.get("pos") or ""):
            c["vertical"] = True

print("cues patched:", hit, " missed:", len(miss))
if miss:
    print("  miss:", miss[:8])

# ---- 同一镜里两句不许落在同一个区（竖排接续除外）：冲突时换到互补锚点
ALT = {
    "center": "low_center", "low_center": "up_center", "up_center": "low_center",
    "low_left": "up_left", "up_left": "low_left",
    "low_right": "up_right", "up_right": "low_right",
    "far_left": "low_left", "far_right": "low_right",
    "right_v": "right_v2", "right_v2": "right_v",
}
for sh in shots:
    cues = sorted([L["cue"] for L in sh.get("layers") or [] if L.get("t") == "type"],
                  key=lambda c: c["t0"])
    prev = None
    for c in cues:
        lay = c.get("layout", "center")
        if prev and lay == prev and not c.get("vertical"):
            lay = ALT.get(lay, lay)
            c["layout"] = lay
            if lay in BAND and BAND[lay]:
                c["band"] = BAND[lay]
        prev = c.get("layout", "center")


# ---------------------------------------------------------------- 3) beats
def near_zcap(sh):
    near = [float(L.get("z", 1.0)) for L in sh.get("layers") or []
            if L.get("t") in ("prop", "figure", "map")]
    return max(0.03, (min(near) if near else 0.9) - 0.12)


def base_cam(sh):
    spec = dict(sh.get("cam") or {})
    spec["nudges"] = []
    spec["beats"] = []
    spec["accents"] = []
    return CAM.Cam(spec)


done = 0
gidx = 0
for sh in shots:
    cam = sh.get("cam") or {}
    cues = sorted([L["cue"] for L in sh.get("layers") or [] if L.get("t") == "type"],
                  key=lambda c: c["t0"])
    cam["nudges"] = []
    cam["handheld"] = 0.55
    cam["beats"] = []
    cam["accents"] = []
    if GRID:
        cam["bpm"] = GRID.get("bpm")
    if not cues:
        continue
    # 片头十张时期卡、片尾不动（保留原节奏）
    if sh["t0"] < 18.0 or sh["t0"] > 244.0:
        continue
    dur = max(0.2, sh["t1"] - sh["t0"])
    zcap = near_zcap(sh)
    bc = base_cam(sh)
    zbase = max(float(k[3]) for k in (cam.get("keys") or [[0, 0, 0, 0, 0, 0.5]]))
    beats, accents = [], []
    for i, c in enumerate(cues):
        gi = gidx
        gidx += 1
        key = norm(c.get("text", ""))
        words = c.get("words") or []
        t_abs = float(words[0]["t0"]) if words else float(c["t0"])
        beat_t = max(0.15, min(dur - 0.10, t_abs - sh["t0"]))
        if key in BEAT_FIX:
            pose, tin, ease, acc = BEAT_FIX[key]
        else:
            pose, ease = default_beat(c.get("layout", "center"), i)
            tin = 0.48
            acc = (14 if pose[0] > 0 else (-14 if pose[0] < 0 else 0),
                   12 if pose[1] > 0 else (-12 if pose[1] < 0 else 0),
                   0.004 if pose[2] > 0 else (-0.004 if pose[2] < 0 else 0), 0.0, 0.0)
        if beat_t < 0.55:
            # 镜头切入时第一句就已经在唱：机位直接落定，入场动作交给换场
            beat_t, tin = 0.02, 0.02
        t = beat_t
        # 夹取：不许把相机推出 z 上限 / 视野
        b = bc.at(t / dur)
        pz = pose[2]
        if pz > 0:
            pz = min(pz, max(0.0, zcap - max(zbase, b[2]) - 0.004))
        px = max(-0.085, min(0.085, pose[0]))
        if abs(b[0] + px) > 0.10:
            px = (0.10 if b[0] + px > 0 else -0.10) - b[0]
            px = max(-0.06, min(0.06, px))
        py = max(-0.07, min(0.07, pose[1]))
        beats.append(dict(t=round(t, 3), **{"in": round(tin, 3)}, ease=ease,
                          pose=[round(px, 4), round(py, 4), round(pz, 4),
                                round(pose[3], 2), round(pose[4], 2)]))
        t_acc = round(snap_beat(sh["t0"] + t) - sh["t0"], 3)
        accents.append(dict(t=t_acc, a=[round(float(v), 4) for v in acc],
                            rise=0.10, fall=0.30))
        # 段落标点：每 4 句一次更大的重音（落在拍点上）
        if gi % 4 == 0:
            accents.append(dict(t=t_acc, a=[20.0, 0.0, 0.004, 0.35, 0.0],
                                rise=0.09, fall=0.34))
        # 末句韵脚补一记轻抬
        if i == len(cues) - 1 and words:
            tl = min(dur - 0.06, float(words[-1]["t0"]) - sh["t0"] + 0.04)
            if tl - t > 0.35:
                accents.append(dict(t=round(snap_beat(sh["t0"] + max(tl, 0.2)) - sh["t0"], 3),
                                    a=[round(acc[0] * 0.55, 4), round(acc[1] * 0.55, 4),
                                       round(acc[2] * 0.55, 4), 0.0, 0.0],
                                    rise=0.09, fall=0.26))
    cam["beats"] = beats
    cam["accents"] = accents
    done += 1

print("shots with beats:", done)

# 4) 文字不得跨场景（沿用 v14 的修法）
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

# 4) 后期节点：scanline / glitch / 溢光按段落给，不再全片一个强度
POST_BASE = dict(scan=0.35, glitch=0.60, bloom=0.28)
STRUCT = (30.90, 108.00, 175.48, 184.24, 207.97, 235.71)
for s in shots:
    t0 = float(s["t0"])
    if t0 < 18.0:
        p = dict(scan=1.00, glitch=0.50, bloom=0.12)
    elif 90.0 <= t0 < 108.0:
        p = dict(scan=0.30, glitch=0.35, bloom=0.50)
    elif 175.0 <= t0 < 183.0:
        p = dict(scan=1.00, glitch=0.85, bloom=0.12)
    elif t0 >= 244.0:
        p = dict(scan=0.70, glitch=0.30, bloom=0.50)
    else:
        p = dict(POST_BASE)
    for st in STRUCT:
        if abs(t0 - st) < 0.30:
            p["glitch"] = 1.40
            p["scan"] = 0.70
    s["post"] = p

# 5) 参考片语法：中间层瘦身 + 层内运动 + 环境在句内换景
#    过期童话一场戏里：机位基本不动（0.1–0.5 px/f），
#    动的是中间层自身（旋转/生长/换形）和环境（图案长出来、色调翻转）。
DROP_FIG = {39.00: "fig_aquinas", 72.35: "fig_locke", 76.39: "fig_hume",
            123.14: "fig_schopenhauer", 159.85: "fig_husserl",
            167.75: "fig_wittgenstein", 182.65: "fig_marcuse", 38.74: "fig_aquinas",
            188.19: "fig_camus", 64.48: "fig_spinoza", 119.34: "fig_marx"}
ADD_PROP = {64.48: dict(t="map", src="map_ancient", z=0.34, x=0.26, y=0.60, w=0.34, alpha=0.42),
            72.35: dict(t="prop", src="stele", z=0.32, x=0.82, y=0.55, h=0.72),
            159.85: dict(t="prop", src="ladder", z=0.32, x=0.24, y=0.52, h=0.78),
            167.75: dict(t="prop", src="frame", z=0.32, x=0.80, y=0.50, h=0.70),
            123.14: dict(t="prop", src="gear", z=0.32, x=0.24, y=0.52, h=0.66),
            188.19: dict(t="prop", src="stele", z=0.32, x=0.22, y=0.55, h=0.70)}

def _near(t, keys, tol=0.03):
    for k in keys:
        if abs(t - k) < tol:
            return k
    return None

for s in shots:
    t0 = float(s["t0"])
    dk = _near(t0, DROP_FIG)
    lay = s.get("layers") or []
    keep = []
    for L in lay:
        if L.get("t") == "figure" and dk is not None and DROP_FIG[dk] == L.get("src"):
            continue
        keep.append(L)
    s["layers"] = keep
    # 空出来的场不再用石碑/梯子/齿轮/地图这些素材去填（用户判定为劣质）
    # 层内运动：人物轻微推近 + 侧移；道具慢转 + 微放大（同一镜内自己动）
    for i, L in enumerate(s["layers"]):
        if L.get("t") in ("figure", "prop") and "h1" not in L:
            h = float(L.get("h", 0.7))
            sgn = 1.0 if i % 2 == 0 else -1.0
            L["h1"] = round(h * 1.04, 3)
            L["x1"] = round(float(L.get("x", 0.5)) + sgn * 0.012, 4)
            if L.get("t") == "prop":
                L["tilt1"] = round(float(L.get("tilt", 0.0)) + sgn * 1.2, 2)

MODES = ["mosaic", "mosaic", "light", "ink"]
for k, s in enumerate(shots):
    cues = sorted([L["cue"] for L in s.get("layers") or [] if L.get("t") == "type"],
                  key=lambda c: c["t0"])
    if len(cues) < 2 or k % 2:
        continue
    bg0 = next((L for L in s.get("layers") or [] if L.get("t") == "bg"), None)
    if not bg0:
        continue
    t_sw = round(float(cues[1].get("words")[0]["t0"]), 3) if cues[1].get("words") else round(cues[1]["t0"], 3)
    s["layers"].append(dict(t="bg", src=bg0.get("src"), idx=int(bg0.get("idx", 0)),
                            z=0.995, mode=MODES[(k // 2) % len(MODES)],
                            palette=bg0.get("palette"), fit=bg0.get("fit", 1.05),
                            alpha=1.0, tin=t_sw - 0.05, dur_in=0.75, paper=False))

json.dump(shots, io.open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", DST)

# 概览
from collections import Counter
lay = Counter()
nb = 0
for s in shots:
    for L in s.get("layers") or []:
        if L.get("t") == "type":
            lay[(L.get("cue") or {}).get("layout", "center")] += 1
    nb += len((s.get("cam") or {}).get("beats") or [])
print("layouts:", lay.most_common())
print("beats total:", nb)
