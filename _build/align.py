# -*- coding: utf-8 -*-
"""Whisper forced-ish transcription: produce word-level timings for the Suno render."""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AUDIO = os.path.join(ROOT, "\u8ffd\u95ee\u4e00\u4e0b.mp3")

def main():
    import whisper
    t0 = time.time()
    print("[whisper] loading small ...", flush=True)
    model = whisper.load_model("small")
    print("[whisper] loaded in %.1fs" % (time.time() - t0), flush=True)

    prompt = ""
    lp = os.path.join(HERE, "lyrics_raw.txt")
    if os.path.exists(lp):
        raw = open(lp, encoding="utf-8").read()
        lines = [l.strip() for l in raw.splitlines()]
        lines = [l for l in lines if l and not l.startswith("[") and not l.startswith("(")]
        prompt = "".join(lines)[:800]
    print("[whisper] initial_prompt head:", prompt[:40], flush=True)

    t1 = time.time()
    res = model.transcribe(
        AUDIO,
        language="zh",
        task="transcribe",
        word_timestamps=True,
        initial_prompt=prompt,
        condition_on_previous_text=False,
        verbose=True,
        fp16=False,
    )
    print("[whisper] transcribe %.1fs" % (time.time() - t1), flush=True)

    out = {"language": res.get("language"), "text": res.get("text"), "segments": []}
    for seg in res["segments"]:
        out["segments"].append({
            "id": seg.get("id"),
            "start": seg["start"],
            "end": seg["end"],
            "text": seg.get("text"),
            "words": [{"w": w.get("word"), "s": w.get("start"), "e": w.get("end")} for w in seg.get("words", [])],
        })
    op = os.path.join(HERE, "asr.json")
    json.dump(out, open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[whisper] wrote", op, len(out["segments"]), "segments", flush=True)

if __name__ == "__main__":
    main()
