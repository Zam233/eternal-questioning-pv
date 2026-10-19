# -*- coding: utf-8 -*-
"""把《文字分镜表》逐句解析成 cue 参数，写进 shots_v16.json。

文档即数据源：表格每个块的「逐字」一行给出每字的大小/高低/微移/旋转/明暗/动作，
「落位」一行给出行轴斜率、字距、散开/竖排/小字/行进/下坠/后退等整句行为。
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pv import typespec as TS          # noqa: E402

DOC = os.path.join(os.path.dirname(HERE), "PV_文字分镜表.md")
SRC = os.path.join(HERE, "shots_v15.json")
DST = os.path.join(HERE, "shots_v16.json")

BLOCK = re.compile(
    r"\*\*(\d{2}) · ([\d.]+)–([\d.]+) · (.+?)\*\*\n"
    r"(?:.*?\n)*?"
    r"落位：(.*?)\n逐字：(.*?)\n出现：(.*?)\n为什么：(.*?)\n", re.S)

text = io.open(DOC, encoding="utf-8").read()
rows = BLOCK.findall(text)
print("blocks parsed:", len(rows))
if len(rows) < 60:
    raise SystemExit("解析到的块太少，检查文档格式")

PUNCT = re.compile(r'[\s\u3000"\u201c\u201d\'\u2018\u2019,，.。!！?？;；:：、]')


def norm(s):
    return PUNCT.sub("", (s or "").strip())


specs = {}
for shot, t0, t1, lyric, pos, glyph_line, appear, why in rows:
    spec = TS.spec_from_block(pos, glyph_line, appear)
    spec["shot"] = shot
    spec["pos"] = pos
    spec["doc_t0"] = float(t0)
    specs[norm(lyric)] = spec

shots = json.load(io.open(SRC, encoding="utf-8"))
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
        gs = spec["glyph"]
        ws = c.get("words") or []
        # 同组大字（连续 ≥1.8 倍）同时落，别一个字一个字蹦
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
        # 小字沉到画面底缘（文档里写"退到画面底边/下缘"的句子）
        low_txt = (spec.get("appear") or "") + (spec.get("pos") or "")
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

print("cues patched:", hit, " missed:", len(miss))
if miss:
    print("  miss:", miss[:8])
json.dump(shots, io.open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", DST)
