# -*- coding: utf-8 -*-
import os, json, subprocess, glob, sys

print("=== whisper cache ===")
cands = [os.path.expanduser("~/.cache/whisper"), os.path.expanduser("~/AppData/Local/whisper")]
for c in cands:
    print(c, "EXISTS" if os.path.isdir(c) else "missing")
    if os.path.isdir(c):
        for f in os.listdir(c):
            p = os.path.join(c, f)
            print("   ", f, os.path.getsize(p))

print("\n=== torch ===")
import torch
print("torch", torch.__version__, "cuda_available", torch.cuda.is_available())
try:
    print("torch threads", torch.get_num_threads())
except Exception as e:
    print(e)
import multiprocessing
print("cpu_count", multiprocessing.cpu_count())

print("\n=== lyrics tag -> file ===")
out = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format_tags", "-of", "json", "\u8ffd\u95ee\u4e00\u4e0b.mp3"],
    capture_output=True,
)
data = json.loads(out.stdout.decode("utf-8", "replace"))
lyr = data.get("format", {}).get("tags", {}).get("lyrics-eng", "")
open(os.path.join(os.path.dirname(__file__), "lyrics_raw.txt"), "w", encoding="utf-8").write(lyr)
print("chars:", len(lyr))
print(lyr)
