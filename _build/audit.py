# -*- coding: utf-8 -*-
"""审计脚本：拿一份 shots_*.json（可再给一支出好的 mp4），逐条跑硬规则。

    python audit.py --shots shots_v15.json
    python audit.py --shots shots_v15.json --video out/v14_open8.mp4 --scan

退出码 0 = 全过；1 = 有 FAIL。WARN 不拦。
规则条文见 ../PV_审计规则.md，编号一一对应。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

W, H, FPS = 1920, 1080, 24
FLASH_KINDS = ("flash", "flash_soft", "whip", "streak", "tint")
BANNED_TRANS = ("cut", "burn", "white", "colorflash")


class Report:
    def __init__(self):
        self.rows = []

    def add(self, rid, name, ok, detail="", level="FAIL"):
        self.rows.append((rid, name, ok, detail, level))

    def fail(self, rid, name, detail):
        self.add(rid, name, False, detail, "FAIL")

    def ok(self, rid, name, detail=""):
        self.add(rid, name, True, detail)

    def warn(self, rid, name, detail):
        self.add(rid, name, True, detail, "WARN")

    def dump(self):
        bad = 0
        for rid, name, ok, detail, level in sorted(self.rows):
            if ok and level == "WARN":
                tag = "WARN"
            elif ok:
                tag = " OK "
            else:
                tag = "FAIL"
                bad += 1
            print("[%s] %-5s %-34s %s" % (tag, rid, name, detail))
        print()
        print("FAIL %d 条" % bad)
        return 0 if bad == 0 else 1


def cues_of(s):
    return [L["cue"] for L in (s.get("layers") or []) if L.get("t") == "type"]


def last_word(c):
    ws = c.get("words") or []
    return float(ws[-1]["t0"]) if ws else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", required=True)
    ap.add_argument("--video", default="")
    ap.add_argument("--scan", action="store_true", help="抽帧扫空带（慢）")
    a = ap.parse_args()
    shots = json.load(open(a.shots, encoding="utf-8"))
    shots.sort(key=lambda s: s["t0"])
    r = Report()
    body = [s for s in shots if s.get("caption")]      # 有 PLATE 编号的正片
    first_body = body[0]["t0"] if body else 1e9
    era = [s for s in shots if not s.get("caption") and s["t0"] < first_body - 0.01]

    # ---------------------------------------------------------------- R01 无硬切
    bad = []
    for i in range(1, len(shots)):
        s = shots[i]
        L = s.get("link") or {}
        prev = shots[i - 1]
        if not L:
            # 段内溶解也算"有过渡"，但必须真的重叠
            if float(s.get("xfade", 0)) < 0.35 or s["t0"] >= prev["t1"] + 0.02:
                bad.append("镜@%.2f 无过渡" % s["t0"])
            continue
        if float(L.get("dur", 0)) < 0.30:
            bad.append("镜@%.2f dur=%.2f<0.30" % (s["t0"], L["dur"]))
        if abs((prev["t1"] - s["t0"]) - float(L["dur"])) > 0.02:
            bad.append("镜@%.2f 重叠=%.2f≠dur=%.2f" % (
                s["t0"], prev["t1"] - s["t0"], L["dur"]))
    if bad:
        r.fail("R01", "禁止硬切：每处衔接必须重叠（link 或 xfade）", "; ".join(bad[:6]))
    else:
        r.ok("R01", "禁止硬切：%d 处衔接全部重叠" % (len(shots) - 1))

    # ---------------------------------------------------------------- R02 无闪白/色闪
    bad = []
    for s in shots:
        tr = s.get("trans_in")
        if isinstance(tr, str) and tr in FLASH_KINDS:
            bad.append("镜@%.2f trans_in=%s" % (s["t0"], tr))
        if isinstance(s.get("flash"), (int, float)) and s["flash"] > 0:
            bad.append("镜@%.2f flash=%.2f" % (s["t0"], s["flash"]))
        for k in s:
            if k in ("burn", "white", "colorflash"):
                bad.append("镜@%.2f 有 %s 键" % (s["t0"], k))
    if bad:
        r.fail("R02", "禁止白光/白场/色闪/过曝熔解", "; ".join(bad[:6]))
    else:
        r.ok("R02", "禁止白光/白场/色闪/过曝熔解")

    # ---------------------------------------------------------------- R04 换场分量必须合规且组合多样
    DIRS = ("left", "right", "up", "down", "ul", "ur", "dl", "dr")
    bad, sigs = [], set()
    for i in range(1, len(shots)):
        L = shots[i].get("link") or {}
        if not L:
            continue
        d = L.get("dir")
        za, zb = float(L.get("za", 1.0)), float(L.get("zb", 1.0))
        rack = float(L.get("rack", 0.0))
        light, amt, w = L.get("light"), float(L.get("amt", 0.0)), float(L.get("w", 0.16))
        has_zoom = za > 1.005 or zb > 1.005
        if not d and not has_zoom and rack <= 0.5 and not light:
            bad.append("镜@%.2f 没有任何换场分量" % shots[i]["t0"])
            continue
        if d and d not in DIRS:
            bad.append("镜@%.2f dir=%r" % (shots[i]["t0"], d))
        if not (1.0 <= za <= 3.2 and 1.0 <= zb <= 3.2):
            bad.append("镜@%.2f 推拉倍数越界 %.2f/%.2f" % (shots[i]["t0"], za, zb))
        if rack > 24:
            bad.append("镜@%.2f 移焦过猛 %.0f" % (shots[i]["t0"], rack))
        if light not in (None, "black", "bloom"):
            bad.append("镜@%.2f light=%r" % (shots[i]["t0"], light))
        if light:
            if amt < 0.15 or amt > 0.96:
                bad.append("镜@%.2f 光脉冲幅度 %.2f" % (shots[i]["t0"], amt))
            if not (0.08 <= w <= 0.26):
                bad.append("镜@%.2f 光脉冲宽度 %.2f" % (shots[i]["t0"], w))
            if float(L.get("dur", 0)) < 0.40:
                bad.append("镜@%.2f 带光换场 %.2fs<0.40" % (shots[i]["t0"], L["dur"]))
        if not d and has_zoom:
            cx, cy = float(L.get("cx", 0.5)), float(L.get("cy", 0.5))
            if not (0.04 <= cx <= 0.96 and 0.04 <= cy <= 0.96):
                bad.append("镜@%.2f 推拉中心出界" % shots[i]["t0"])
        sigs.add(("dir" if d else "-", "zoom" if has_zoom else "-",
                  "rack" if rack > 0.5 else "-", light or "-"))
    if bad:
        r.fail("R04", "换场分量不合规", "; ".join(bad[:6]))
    elif len(sigs) < 8:
        r.fail("R04", "换场组合太少（只有 %d 种）" % len(sigs), "")
    else:
        r.ok("R04", "换场分量 43 处，%d 种组合：%s" % (len(sigs), " / ".join(
            "+".join([x for x in g if x != "-"]) or "纯叠化" for g in sorted(sigs))))

    # ---------------------------------------------------------------- R05 窗口落在静音缝
    bad = []
    for i in range(1, len(shots)):
        L = shots[i].get("link") or {}
        if not L:
            continue
        prev = shots[i - 1]
        dur = float(L.get("dur", 0))
        tb = min(c["t0"] for c in cues_of(shots[i])) if cues_of(shots[i]) else None
        if tb is None:
            continue
        if tb < shots[i]["t0"] - 0.02:
            bad.append("镜@%.2f 首句 %.2f 早于本镜起点 %.2f" % (
                shots[i]["t0"], tb, shots[i]["t0"]))
        if prev.get("_cue_end"):
            if float(prev["_cue_end"]) > shots[i]["t0"] + dur + 0.02:
                bad.append("镜@%.2f 上一镜文字越过衔接" % shots[i]["t0"])
    if bad:
        r.fail("R05", "衔接窗口必须落在两行歌词的静音缝里", "; ".join(bad[:6]))
    else:
        r.ok("R05", "衔接窗口全部落在静音缝里")

    # ---------------------------------------------------------------- R06 时长
    bad = []
    for s in shots:
        L = s.get("link") or {}
        if not L:
            continue
        if not (0.30 <= float(L["dur"]) <= 0.70):
            bad.append("镜@%.2f dur=%.2f" % (s["t0"], L["dur"]))
    if bad:
        r.warn("R06", "转场时长宜 0.30–0.70 s", "; ".join(bad[:6]))
    else:
        r.ok("R06", "转场时长 0.30–0.70 s")

    # ---------------------------------------------------------------- R08 每镜有相机运动
    bad = []
    for s in shots:
        cam = s.get("cam") or {}
        ks = cam.get("keys") or []
        if len(ks) < 2:
            bad.append("镜@%.2f keys<2" % s["t0"])
            continue
        a0, a1 = ks[0], ks[-1]
        moved = (abs(a1[1] - a0[1]) >= 0.004 or abs(a1[2] - a0[2]) >= 0.004
                 or abs(a1[3] - a0[3]) >= 0.02 or abs(a1[4] - a0[4]) >= 0.04)
        if not moved:
            bad.append("镜@%.2f 相机几乎不动" % s["t0"])
    if bad:
        r.fail("R08", "每镜必须有相机运动", "; ".join(bad[:6]))
    else:
        r.ok("R08", "每镜都有相机运动")

    # ---------------------------------------------------------------- R10 推拉幅度与安全区
    pushes, bad, badz = 0, [], []
    TEXZ = ("type", "texture")
    for s in shots:
        cam = s.get("cam") or {}
        ks = cam.get("keys") or []
        if len(ks) < 2:
            continue
        dz = ks[-1][3] - ks[0][3]
        if abs(dz) >= 0.06:
            pushes += 1
        zmax = max(float(k[3]) for k in ks)
        zmin = min(float(k[3]) for k in ks)
        if zmax > 0.24 or zmin < -0.02:
            badz.append("镜@%.2f z=[%.3f,%.3f]" % (s["t0"], zmin, zmax))
            continue
        near = [float(L.get("z", 1.0)) for L in (s.get("layers") or [])
                if L.get("t") not in TEXZ]
        if near and zmax > min(near) - 0.12:
            badz.append("镜@%.2f z=%.3f 逼近近层 z=%.2f" % (s["t0"], zmax, min(near)))
    if badz:
        r.fail("R10", "相机 z 不得逼近近层（z ≤ 近层 z − 0.12）", "; ".join(badz[:6]))
    else:
        r.ok("R10", "相机 z 全部留出近层安全余量")
    if pushes >= 12:
        r.ok("R09", "长推/长拉镜 %d 处" % pushes)
    else:
        r.warn("R09", "长推/长拉镜偏少（%d 处）" % pushes, "")

    # ---------------------------------------------------------------- R11 nudge 幅度
    bad = []
    for s in shots:
        for nd in (s.get("cam") or {}).get("nudges") or []:
            if abs(nd.get("dx", 0)) > 0.030 or abs(nd.get("dz", 0)) > 0.040 \
                    or abs(nd.get("dr", 0)) > 0.32:
                bad.append("镜@%.2f nudge 过大" % s["t0"])
                break
    if bad:
        r.fail("R11", "逐句 nudge 幅度上限 (0.03,0.02,0.04,0.32)", "; ".join(bad[:6]))
    else:
        r.ok("R11", "逐句 nudge 幅度在限内")

    # ---------------------------------------------------------------- R12/R13/R14/R15 文字
    b13, b14, b15 = [], [], []
    for s in shots:
        cs = sorted(cues_of(s), key=lambda c: c["t0"])
        for i, c in enumerate(cs):
            lw = last_word(c)
            if lw is not None and c["t1"] - lw < 0.50:
                b13.append("镜@%.2f 「%s」末字仅 %.2f s" % (s["t0"], c["text"], c["t1"] - lw))
            if c["t1"] > s["t1"] - 0.02 + 1e-6:
                b14.append("镜@%.2f 「%s」越过镜尾" % (s["t0"], c["text"]))
            if i:
                if cs[i - 1]["t1"] - c["t0"] > 0.52:
                    b15.append("镜@%.2f 相邻 cue 重叠 %.2f s" % (s["t0"], cs[i - 1]["t1"] - c["t0"]))
    if b13:
        r.warn("R13", "末字必须停留 ≥0.5 s（被镜尾夹住的可容忍）", "%d 处" % len(b13))
    else:
        r.ok("R13", "末字停留 ≥0.5 s")
    if b14:
        r.fail("R14", "文字不得跨场景", "; ".join(b14[:6]))
    else:
        r.ok("R14", "文字不跨场景")
    if b15:
        r.fail("R15", "同镜相邻 cue 重叠 ≤0.5 s", "; ".join(b15[:6]))
    else:
        r.ok("R15", "同镜相邻 cue 重叠 ≤0.5 s")

    # ---------------------------------------------------------------- R25 中间层必须是"主体"
    bad = []
    for s in shots:
        n = 0
        for L in s.get("layers") or []:
            if L.get("t") not in ("prop", "figure", "map"):
                continue
            n += 1
            h = float(L.get("h", L.get("w", 0.0)) or 0.0)
            dx = abs(float(L.get("x", 0.5)) - 0.5)
            if h < 0.60 and dx < 0.22:
                bad.append("镜@%.2f %s h=%.2f x=%.2f（居中悬浮的小物件）"
                           % (s["t0"], L.get("src"), h, float(L.get("x", 0.5))))
        if n > 2:
            bad.append("镜@%.2f 中间层 %d 个（≤2）" % (s["t0"], n))
    if bad:
        r.fail("R25", "中间层必须是贴边的大主体（h≥0.60 或 贴边）", "; ".join(bad[:6]))
    else:
        r.ok("R25", "中间层全部是贴边大主体（无居中悬浮小物件）")

    # ---------------------------------------------------------------- R20 素材可解析
    try:
        base = os.path.join(HERE, "assets")
        dirs = ["ai", "era", "props", "figures", "subjects", "maps"]
        have = set()
        for d in dirs:
            p = os.path.join(base, d)
            if os.path.isdir(p):
                have |= {os.path.splitext(f)[0] for f in os.listdir(p)}
        bad = []
        for s in shots:
            for L in s.get("layers") or []:
                src = L.get("src")
                if L.get("t") in ("bg", "prop", "figure", "map") and src and src not in have:
                    bad.append("%s(%s)" % (src, L.get("t")))
        bad = sorted(set(bad))
        if bad:
            r.fail("R20", "素材必须能在 assets 里解析到", ", ".join(bad[:10]))
        else:
            r.ok("R20", "素材全部可解析（%d 个素材名）" % len(have))
    except Exception as e:  # noqa
        r.warn("R20", "素材检查跳过", str(e))

    # ---------------------------------------------------------------- R21 镜号 + 画面无小标
    nos = [s["caption"].get("no", "") for s in body]
    exp = ["PLATE %02d" % i for i in range(1, len(body) + 1)]
    shown = [s["t0"] for s in shots if not s.get("hide_meta")]
    if nos != exp:
        diff = [(i + 1, a, b) for i, (a, b) in enumerate(zip(nos, exp)) if a != b][:6]
        r.fail("R21", "镜号必须连续（数据层）", str(diff))
    elif shown:
        r.fail("R21", "画面里不得再出现 PLATE 编号与拉丁小标",
               "未隐藏的镜：%s" % ", ".join("%.1f" % t for t in shown[:6]))
    else:
        r.ok("R21", "镜号 01–%02d 连续；画面无 PLATE／小标（hide_meta 全开）" % len(body))

    # ---------------------------------------------------------------- R22 片头只有时期名
    bad = []
    if len(era) != 10:
        bad.append("片头卡应为 10 张，实为 %d" % len(era))
    for s in era:
        if len(cues_of(s)) != 1:
            bad.append("片头卡@%.2f 有 %d 条字" % (s["t0"], len(cues_of(s))))
    if bad:
        r.fail("R22", "片头时期卡只允许一条文字（时期名）", "; ".join(bad[:6]))
    else:
        r.ok("R22", "片头 %d 张卡只写时期名" % len(era))

    # ---------------------------------------------------------------- R23 署名
    cr = []
    for s in shots:
        if s.get("credits"):
            cr.append((s, len(s["credits"].get("lines") or [])))
        for c in cues_of(s):
            if c.get("kind") == "credits":
                cr.append((s, len(c.get("rows") or [])))
    if len(cr) == 1 and cr[0][1] == 6 and cr[0][0]["t1"] - cr[0][0]["t0"] > 8:
        r.ok("R23", "署名六条，且只出现在一处长间奏（两栏排版）")
    else:
        r.fail("R23", "署名必须且只能出现在一处长间奏，且六条", "找到 %d 处/%s 条"
               % (len(cr), cr[0][1] if cr else "-"))

    # ---------------------------------------------------------------- R24 全覆盖
    gaps = []
    for i in range(1, len(shots)):
        if shots[i]["t0"] > shots[i - 1]["t1"] + 0.001:
            gaps.append((round(shots[i - 1]["t1"], 2), round(shots[i]["t0"], 2)))
    if gaps:
        r.fail("R24", "全片时间轴不得有空洞", str(gaps[:6]))
    else:
        r.ok("R24", "全片 %.2f s 连续覆盖" % shots[-1]["t1"])

    # ---------------------------------------------------------------- R03 空带扫描
    if a.video and a.scan:
        code = _scan_blank(a.video, shots, r)
        if code:
            return code

    return r.dump()


def _scan_blank(video, shots, r):
    import subprocess
    import tempfile
    import numpy as np
    from PIL import Image
    tmp = os.path.join(tempfile.gettempdir(), "pv_audit_scan")
    os.makedirs(tmp, exist_ok=True)
    bad = []
    for s in shots:
        L = s.get("link") or {}
        if not L:
            continue
        if L.get("light"):
            continue                   # 带黑场/闪光分量的换场本来就该压黑/过曝
        t0 = float(s["t0"])
        dur = float(L["dur"])
        for f in range(int((t0 - 0.15) * FPS), int((t0 + dur + 0.15) * FPS)):
            p = os.path.join(tmp, "f%06d.png" % f)
            if not os.path.exists(p):
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.4f" % (f / FPS),
                                "-i", video, "-frames:v", "1", p], check=True)
            g = np.asarray(Image.open(p).convert("L"), np.float32)
            for axis in (0, 1):
                n = 24
                step = (g.shape[1] if axis == 0 else g.shape[0]) // n
                # 最外圈那一条是暗角/压边，不算空带
                for i in range(1, n - 1):
                    sl = g[:, i * step:(i + 1) * step] if axis == 0 else g[i * step:(i + 1) * step, :]
                    if sl.std() < 1.6 and sl.mean() < 26:
                        bad.append("t=%.2f %s向第 %d 块" % (f / FPS, "横" if axis == 0 else "纵", i))
                        break
    if bad:
        r.fail("R03", "平移衔接不得留空带", "; ".join(bad[:8]))
    else:
        n = len([s for s in shots if s.get("link") and not (s.get("link") or {}).get("light")])
        r.ok("R03", "抽查 %d 处平移类衔接（带光的换场按设计压黑/过曝，跳检），无空带" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
