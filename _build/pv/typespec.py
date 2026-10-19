# -*- coding: utf-8 -*-
"""逐字排版规格（typespec）：把文字分镜表里的写法直接变成引擎参数。

文档里的写法长这样（每个字一项）：

    毒×2.6↑0[砸]   囚×1.6↑12[被挡]   燃×1.35↑6[亮1.0→0.5]   异×1.7↑6[左移0.05W]

本模块把它解析成：

    dict(s=2.6, dy=0.0, dx=0.0, r=0.0, a=1.0, a1=None, act="slam", note="砸")

另外从"落位"一句里抽行轴斜率与字距：

    行轴 +1.5°   → slope = 1.5
    字距 1.7em   → track  = 1.7
"""
import re

_SCALE = re.compile(r"×\s*([0-9.]+)")
_DY = re.compile(r"([↑↓])\s*([0-9.]+)")
_DX = re.compile(r"[（(]?\s*(左|右)移\s*([0-9.]+)\s*W\s*[）)]?")
_ROT = re.compile(r"旋\s*(-?[0-9.]+)\s*°")
_ALPHA = re.compile(r"透明(?:度)?\s*([0-9.]+)")
_BURN = re.compile(r"亮\s*([0-9.]+)\s*→\s*([0-9.]+)")
_BLOCK = re.compile(r"[（(]([^）)]*)[）)]")
_ACT = re.compile(r"\[([^\]]+)\]")

ACTIONS = [
    ("砸", "slam"), ("印", "stamp"), ("撞入", "slam"), ("撞", "slam"),
    ("落定", "land"), ("落", "land"),
    ("抬起", "lift"), ("抬", "lift"), ("浮", "lift"),
    ("擦除", "wipe"), ("擦入", "wipe"), ("擦", "wipe"),
    ("划掉", "strike"), ("划", "strike"),
    ("切成片", "cut"), ("切", "cut"),
    ("复制", "copy"), ("燃", "burn"), ("颤动", "tremble"), ("颤", "tremble"),
    ("退场", "retreat"), ("退", "retreat"), ("被挡", "behind"),
    ("先出", "early"), ("最后落", "late"), ("落得慢", "slow"),
]


def _act_of(note):
    for key, code in ACTIONS:
        if key in note:
            return code
    return None


def parse_glyphs(s):
    """'毒×2.6↑0[砸]　鸩×1.1↓8' -> [dict, dict]"""
    out = []
    if not s:
        return out
    for tok in re.split(r"[\s\u3000]+", s.strip()):
        if not tok:
            continue
        m = re.match(r"^([^\s×↑↓（(\[]+)", tok)
        if not m:
            continue
        ch = m.group(1)
        g = dict(ch=ch, s=1.0, dy=0.0, dx=0.0, r=0.0, a=1.0, a1=None,
                 act=None, note="")
        ms = _SCALE.search(tok)
        if ms:
            g["s"] = float(ms.group(1))
        md = _DY.search(tok)
        if md:
            v = float(md.group(2))
            g["dy"] = -v if md.group(1) == "↑" else v
        mdx = _DX.search(tok)
        if mdx:
            v = float(mdx.group(2)) * 100.0
            g["dx"] = v if mdx.group(1) == "左" else -v
        mr = _ROT.search(tok)
        if mr:
            g["r"] = float(mr.group(1))
        ma = _ALPHA.search(tok)
        if ma:
            g["a"] = float(ma.group(1))
        mb = _BURN.search(tok)
        if mb:
            g["a"] = float(mb.group(1))
            g["a1"] = float(mb.group(2))
            g["act"] = "burn"
        act = _ACT.search(tok)
        if act:
            g["note"] = act.group(1)
            g["act"] = g["act"] or _act_of(act.group(1))
        out.append(g)
    return out


def parse_slope(s):
    m = re.search(r"行轴\s*([+-]?[0-9.]+)\s*°", s or "")
    return float(m.group(1)) if m else 0.0


def parse_track(s):
    m = re.search(r"字距\s*([0-9.]+)\s*em", s or "")
    return float(m.group(1)) if m else None


def parse_parts(s):
    """'将×0.8　信×1.75↑10　仰×1.8↑12 ／ 上半句…' -> 按 ／ 分段"""
    if not s:
        return []
    return [p for p in re.split(r"[／/]", s) if p.strip()]


def spec_from_block(pos, glyph_line, appear):
    """从表格一行的三段文字生成一个 cue 的排版参数。"""
    parts = parse_parts(glyph_line)
    glyphs, segs = [], []
    for k, part in enumerate(parts):
        gs = parse_glyphs(part)
        segs.append(dict(start=len(glyphs), n=len(gs), idx=k, total=len(parts)))
        glyphs.extend(gs)
    spec = dict(
        glyph=glyphs,
        segs=segs,
        slope=parse_slope(pos),
        track=parse_track(pos) if parse_track(pos) is not None else parse_track(glyph_line),
        appear=appear or "",
    )
    low = (pos or "") + (appear or "")
    spec["split"] = len(parts) > 1
    spec["reverse"] = ("从右往左" in low) or ("相反" in low)
    spec["scatter"] = ("散开" in low) or ("散在" in low)
    spec["vertical"] = "竖排" in low
    spec["small"] = "小字" in low or "极小字" in low
    spec["drift"] = 0.0
    m = re.search(r"向右行进|向右平移|向右出画", low)
    if m:
        spec["drift"] = 0.004 if "行进" in low else 0.18
    m2 = re.search(r"下坠|向下压|下沉", low)
    spec["sink"] = 0.02 if m2 else 0.0
    spec["retreat"] = ("后退" in low) or ("缩小" in low)
    spec["rise"] = ("上浮" in low) or ("往上" in low) or ("向上" in low)
    spec["stagger"] = 0.0
    return spec
