# -*- coding: utf-8 -*-
"""把 _ref 里的抽样帧匹配回 过期童话.mp4 的时间点（粗匹配，用于定位场景）。"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

VID = r"K:\5A大作\过期童话.mp4"
W, H = 64, 36


def video_frames():
    cmd = ["ffmpeg", "-v", "error", "-i", VID, "-vf", f"scale={W}:{H}",
           "-pix_fmt", "gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
    return arr


def sig(path, size=(W, H)):
    im = Image.open(path).convert("L").resize(size, Image.BILINEAR)
    a = np.asarray(im, np.float32).ravel()
    a = a - a.mean()
    n = np.linalg.norm(a)
    return a / (n + 1e-6)


def main():
    fr = video_frames()
    print("video frames", len(fr), "fps 24")
    # 归一化视频帧向量
    V = fr.reshape(len(fr), -1)
    V = V - V.mean(axis=1, keepdims=True)
    V = V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-6)
    out = {}
    for name in ["fxa", "fxb", "fxc", "fxd", "fxe", "m76"]:
        fs = sorted(glob.glob(rf"K:\5A大作\_ref\{name}\*.jpg"))
        picks = [fs[0], fs[len(fs) // 2], fs[-1]]
        hits = []
        for p in picks:
            q = sig(p)
            corr = V @ q
            idx = int(np.argmax(corr))
            hits.append((os.path.basename(p), idx, round(idx / 24.0, 2),
                         round(float(corr[idx]), 3)))
        out[name] = hits
        print(name, hits)
    json.dump(out, open(r"K:\5A大作\_build\ref_match.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
