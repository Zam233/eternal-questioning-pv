# -*- coding: utf-8 -*-
"""Align the known Suno lyric lines to whisper word timings -> lines.json"""
import json, os, re, difflib, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
PUNCT = set(" \t\u3000\uff0c\u3002\uff1f\uff01\uff1b\uff1a\u201c\u201d\u2018\u2019\u3001\uff08\uff09(),.!?;:\"'-")

def norm(ch):
    if ch in PUNCT:
        return ""
    return ch

def load_known():
    raw = open(os.path.join(HERE, "lyrics_raw.txt"), encoding="utf-8").read()
    lines, section = [], "intro"
    for ln in raw.splitlines():
        s = ln.strip()
        if not s or s.startswith("("):
            continue
        if s.startswith("["):
            section = s.strip("[]").split("-")[0].strip().lower().replace(" ", "")
            continue
        lines.append({"raw": s, "section": section})
    return lines

def asr_chars():
    d = json.load(open(os.path.join(HERE, "asr.json"), encoding="utf-8"))
    out = []
    for seg in d["segments"]:
        ws = seg.get("words") or []
        for w in ws:
            txt = w.get("w") or ""
            chars = [c for c in txt if norm(c)]
            if not chars:
                continue
            s, e = w.get("s"), w.get("e")
            if s is None or e is None or e <= s:
                s, e = seg["start"], seg["end"]
            n = len(chars)
            for i, c in enumerate(chars):
                out.append({"c": c, "s": s + (e - s) * i / n, "e": s + (e - s) * (i + 1) / n})
    return out

def main():
    known = load_known()
    ach = asr_chars()
    kseq, kmap = [], []
    for li, ln in enumerate(known):
        for ci, ch in enumerate(ln["raw"]):
            if norm(ch):
                kseq.append(ch)
                kmap.append((li, ci))
    aseq = [a["c"] for a in ach]

    sm = difflib.SequenceMatcher(None, kseq, aseq, autojunk=False)
    times = [None] * len(kseq)
    identity = (len(kseq) == len(aseq))
    if identity:
        for i in range(len(kseq)):
            times[i] = (ach[i]["s"], ach[i]["e"])
    else:
        for a, b, size in sm.get_matching_blocks():
            for i in range(size):
                times[a + i] = (ach[b + i]["s"], ach[b + i]["e"])

    # interpolate gaps
    known_idx = [i for i, t in enumerate(times) if t]
    if not known_idx:
        raise SystemExit("no matches at all")
    for i in range(len(times)):
        if times[i] is None:
            prev = max([j for j in known_idx if j < i], default=None)
            nxt = min([j for j in known_idx if j > i], default=None)
            if prev is None:
                times[i] = times[nxt]
            elif nxt is None:
                times[i] = times[prev]
            else:
                a, b = times[prev], times[nxt]
                f = (i - prev) / (nxt - prev)
                times[i] = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)

    lines = []
    for li, ln in enumerate(known):
        idxs = [i for i, (l, c) in enumerate(kmap) if l == li]
        if not idxs:
            continue
        t0 = times[idxs[0]][0]
        t1 = times[idxs[-1]][1]
        lines.append({"text": ln["raw"], "section": ln["section"], "t0": round(t0, 3), "t1": round(t1, 3),
                      "words": [{"c": kseq[i], "t0": round(times[i][0], 3), "t1": round(times[i][1], 3)} for i in idxs]})

    # sanity: monotonic, non-overlapping
    for i in range(1, len(lines)):
        if lines[i]["t0"] < lines[i - 1]["t0"]:
            lines[i]["t0"] = lines[i - 1]["t0"]
        if lines[i]["t1"] <= lines[i]["t0"]:
            lines[i]["t1"] = lines[i]["t0"] + 0.4
        if i and lines[i]["t0"] < lines[i - 1]["t1"]:
            lines[i]["t0"] = lines[i - 1]["t1"]

    json.dump(lines, open(os.path.join(HERE, "lines.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    ratio = sum(len(b) for b in sm.get_matching_blocks()) / max(1, len(kseq))
    print("known chars", len(kseq), "asr chars", len(aseq), "match ratio %.3f" % ratio)
    print("%-8s %-7s %-7s %s" % ("section", "t0", "t1", "text"))
    for l in lines:
        print("%-8s %6.2f  %6.2f  %s" % (l["section"], l["t0"], l["t1"], l["text"]))

if __name__ == "__main__":
    main()
