# -*- coding: utf-8 -*-
"""Forced alignment of the KNOWN lyrics to the song (no human stamping).

stable-ts `model.align(audio, text)` runs DTW against whisper's cross-attention
with the transcript supplied, so it cannot hallucinate or drift the way a plain
transcription can. Output: timing_auto.json (same schema as lines.json but with
per-character onsets).
"""
import json, io, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AUDIO = os.path.join(ROOT, "\u8ffd\u95ee\u4e00\u4e0b.mp3")
BASE = os.environ.get("PV_MODELS", os.path.join(ROOT, "_models"))
MODELS = os.path.join(BASE, "dsh_models")
LIB = os.path.join(BASE, "dsh_lib")
TMP = os.environ.get("TMP", os.path.join(ROOT, "_tmp"))

os.environ["TMP"] = TMP
os.environ["TEMP"] = TMP
os.environ["XDG_CACHE_HOME"] = MODELS
if LIB not in sys.path:
    sys.path.insert(0, LIB)

DROP = {"\u8fa9\u9a73\u91cc\u6709\u8c01\u5c06\u4fe1\u4ef0",
        "\u60df\u6709\u76f4\u9762\u8352\u8c2c\u51b3\u610f\u81ea\u51b3\u7684\u4f60\u6211"}
PUNCT = set(" \t\u3000\uff0c\u3002\uff1f\uff01\uff1b\uff1a\u201c\u201d\u2018\u2019\u3001\uff08\uff09(),.!?;:\"'")


def known_lines():
    lines = json.load(io.open(os.path.join(HERE, "lines.json"), encoding="utf-8"))
    seen, kept = set(), []
    for l in lines:
        t = l["text"].replace("\u201c", '"').replace("\u201d", '"').strip()
        if t in DROP:
            if t in seen:
                continue
            seen.add(t)
        l["text"] = t
        kept.append(l)
    return kept


def main():
    import stable_whisper
    t0 = time.time()
    print("[align] loading model ...", flush=True)
    model = stable_whisper.load_model("small", download_root=MODELS)
    print("[align] model ready %.0fs" % (time.time() - t0), flush=True)

    kept = known_lines()
    text = "\n".join(l["text"] for l in kept)
    print("[align] lines %d chars %d" % (len(kept), sum(len(l["text"]) for l in kept)), flush=True)

    t1 = time.time()
    result = model.align(AUDIO, text, language="zh")
    print("[align] align done %.0fs" % (time.time() - t1), flush=True)

    words = []
    for seg in result.segments:
        for w in seg.words:
            s, e = float(w.start), float(w.end)
            for ch in w.word:
                if ch not in PUNCT:
                    words.append((ch, s, e))
    print("[align] words/chars:", len(words), flush=True)

    # expand each word over its characters, then walk the known text
    flat = []
    for ch, s, e in words:
        flat.append((ch, s, e))
    out = []
    wi = 0
    total_chars = sum(len([c for c in l["text"] if c not in PUNCT]) for l in kept)
    print("[align] known chars:", total_chars, "asr chars:", len(flat), flush=True)

    for l in kept:
        cs = [c for c in l["text"] if c not in PUNCT]
        ws = []
        for k, ch in enumerate(cs):
            if wi < len(flat):
                a, b = flat[wi][1], flat[wi][2]
            else:
                a, b = l["t0"], l["t1"]
            ws.append({"c": ch, "t0": round(a, 3), "t1": round(b, 3)})
            wi += 1
        out.append({"text": l["text"], "section": l.get("section", ""),
                    "t0": ws[0]["t0"] if ws else l["t0"],
                    "t1": ws[-1]["t1"] if ws else l["t1"], "words": ws})

    op = os.path.join(HERE, "timing_auto.json")
    json.dump(out, io.open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # sanity report
    bad = []
    for l in out:
        d = l["t1"] - l["t0"]
        if d < 0.6 or d > 8.0:
            bad.append((l["text"], round(l["t0"], 2), round(d, 2)))
    print("[align] wrote", op, "| odd lines:", len(bad))
    for b in bad[:12]:
        print("   ", b)


if __name__ == "__main__":
    main()
