# -*- coding: utf-8 -*-
"""CLI: render stills for review, or the whole film into ffmpeg."""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import config as C
from . import scene as S

SHOTS = None


def load_shots(path):
    shots = json.load(open(path, encoding="utf-8"))
    shots.sort(key=lambda s: s["t0"])
    return shots


def shot_at(shots, t):
    lo, hi = 0, len(shots) - 1
    best = shots[0]
    while lo <= hi:
        mid = (lo + hi) // 2
        s = shots[mid]
        if t < s["t0"]:
            hi = mid - 1
        elif t > s["t1"]:
            lo = mid + 1
        else:
            return s
    # outside: clamp
    if t <= shots[0]["t0"]:
        return shots[0]
    return shots[-1]


def _render_index(args):
    idx, shots_path = args
    global SHOTS
    if SHOTS is None:
        SHOTS = load_shots(shots_path)
    from . import config as CC
    t = idx / CC.FPS
    sh = shot_at(SHOTS, t)
    arr = S.render_frame(sh, t)
    return np.clip(arr, 0, 255).astype(np.uint8).tobytes()


def cmd_stills(shots_path, times, outdir):
    os.makedirs(outdir, exist_ok=True)
    shots = load_shots(shots_path)
    for t in times:
        t0 = time.time()
        from . import frames as FR
        sh = shot_at(shots, t)
        arr = FR.frame_at(shots, t)
        im = S.finish(arr)
        p = os.path.join(outdir, f"still_{t:07.2f}.png")
        im.save(p)
        print(f"{p}  shot={sh.get('title','')}  {time.time()-t0:.2f}s", flush=True)


def cmd_frames(shots_path, out, start=0, end=None, workers=12, crf="17", preset="medium"):
    shots = load_shots(shots_path)
    end = C.NFRAMES if end is None else end
    dur = (end - start) / C.FPS
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    codec = os.environ.get("PV_CODEC", "nvenc")
    if codec == "nvenc":
        venc = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", crf,
                "-b:v", "0", "-maxrate", "120M", "-bufsize", "240M",
                "-profile:v", "high", "-pix_fmt", "yuv420p"]
    else:
        venc = ["-c:v", "libx264", "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p",
                "-x264-params", "keyint=48:min-keyint=24:scenecut=0"]
    audio_in = ["-i", C.AUDIO] if start == 0 else ["-ss", f"{start / C.FPS:.4f}", "-i", C.AUDIO]
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{C.W}x{C.H}", "-r", str(C.FPS),
        "-i", "-",
    ] + audio_in + [
        "-map", "0:v", "-map", "1:a",
    ] + venc + [
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{dur:.3f}",
        "-movflags", "+faststart",
        out,
    ]
    print("ffmpeg:", " ".join(cmd[:12]), "...", flush=True)
    logpath = os.path.join(os.path.dirname(out) or ".", "ffmpeg.log")
    logf = open(logpath, "wb")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=logf)

    global SHOTS
    SHOTS = shots
    t0 = time.time()
    n = 0
    step = max(1, workers) * 4
    total = end - start

    def render_one(i):
        from . import config as CC
        from . import frames as FR
        t = i / CC.FPS
        arr = FR.frame_at(shots, t)
        return np.clip(arr, 0, 255).astype(np.uint8).tobytes()

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for base in range(start, end, step):
            batch = list(range(base, min(end, base + step)))
            for buf in ex.map(render_one, batch):
                proc.stdin.write(buf)
                n += 1
            if n % 96 == 0 or n == total:
                el = time.time() - t0
                rate = n / el
                eta = (total - n) / max(1e-6, rate)
                print(f"  {n}/{total} frames  {rate:.2f} f/s  eta {eta/60:.1f} min", flush=True)

    proc.stdin.close()
    proc.wait()
    logf.close()
    if proc.returncode != 0:
        print("ffmpeg failed, see", logpath, flush=True)
        print(open(logpath, "rb").read()[-1500:].decode("utf-8", "replace"), flush=True)
        raise SystemExit(1)
    print("wrote", out, f"{time.time()-t0:.0f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["stills", "frames", "probe"])
    ap.add_argument("--shots", default=os.path.join(C.BUILD, "shots.json"))
    ap.add_argument("--out", default=os.path.join(C.OUT, "film.mp4"))
    ap.add_argument("--stills-dir", default=os.path.join(C.BUILD, "stills"))
    ap.add_argument("--times", default="")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--crf", default="17")
    ap.add_argument("--preset", default="medium")
    a = ap.parse_args()

    if a.mode == "stills":
        times = [float(x) for x in a.times.split(",") if x.strip()]
        cmd_stills(a.shots, times, a.stills_dir)
    elif a.mode == "frames":
        cmd_frames(a.shots, a.out, a.start, a.end or None, a.workers, a.crf, a.preset)
    else:
        shots = load_shots(a.shots)
        print(len(shots), "shots", sum(s["t1"] - s["t0"] for s in shots), "s covered")
        gaps = []
        for i in range(1, len(shots)):
            if shots[i]["t0"] > shots[i - 1]["t1"] + 0.01:
                gaps.append((shots[i - 1]["t1"], shots[i]["t0"]))
        print("gaps:", gaps[:20])


if __name__ == "__main__":
    main()
