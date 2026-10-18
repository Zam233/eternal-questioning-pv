# -*- coding: utf-8 -*-
import json, io, sys
ls = json.load(io.open("lines.json", encoding="utf-8"))
DROP = {"\u8fa9\u9a73\u91cc\u6709\u8c01\u5c06\u4fe1\u4ef0", "\u60df\u6709\u76f4\u9762\u8352\u8c2c\u51b3\u610f\u81ea\u51b3\u7684\u4f60\u6211"}
seen, kept = set(), []
for l in ls:
    t = l["text"].replace("\u201c", '"').replace("\u201d", '"').strip()
    if t in DROP:
        if t in seen:
            continue
        seen.add(t)
    l["text"] = t
    kept.append(l)
CAP = 6.2
for l in kept:
    if l["t1"] - l["t0"] > CAP:
        l["t1"] = l["t0"] + CAP
    if l["t1"] <= l["t0"]:
        l["t1"] = l["t0"] + 0.8
for i in range(1, len(kept)):
    if kept[i]["t0"] < kept[i - 1]["t1"]:
        kept[i]["t0"] = kept[i - 1]["t1"]
    if kept[i]["t1"] <= kept[i]["t0"]:
        kept[i]["t1"] = kept[i]["t0"] + 0.8
out = ["%2d|%s|%6.2f|%6.2f|%.2f|%s" % (i, l["section"], l["t0"], l["t1"], l["t1"] - l["t0"], l["text"]) for i, l in enumerate(kept)]
io.open("kept_lines.txt", "w", encoding="utf-8").write("\n".join(out))
print("kept", len(kept))
