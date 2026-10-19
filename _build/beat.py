# -*- coding: utf-8 -*-
"""BPM / 拍点估计：不依赖 librosa，用 scipy + numpy 做谱通量 + 自相关。

产物 beat_grid.json：
    {"bpm": 120.0, "period": 0.5, "phase": 0.12, "beats": [0.12, 0.62, ...]}

用法：
    python beat.py            # 估计 + 写文件
"""
import json
import os
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import stft

HERE = os.path.dirname(os.path.abspath(__file__))
WAV = os.path.join(HERE, "_audio_mono.wav")
OUT = os.path.join(HERE, "beat_grid.json")


def onset_env(path):
    sr, x = wavfile.read(path)
    x = x.astype(np.float32) / 32768.0
    f, t, Z = stft(x, fs=sr, nperseg=1024, noverlap=768, boundary=None)
    mag = np.abs(Z)
    flux = np.diff(mag, axis=1)
    flux = np.maximum(flux, 0).sum(axis=0)
    # 去掉低频漂移、归一化
    k = 9
    base = np.convolve(flux, np.ones(k) / k, mode="same")
    env = np.maximum(flux - base, 0)
    if env.max() > 0:
        env = env / env.max()
    return t[1:], env


def estimate(t, env):
    dt = float(np.median(np.diff(t)))
    # 自相关（只看 60–180 BPM 的滞后）
    e = env - env.mean()
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    ac /= ac[0] + 1e-9
    lo = int(60.0 / 180.0 / dt)
    hi = int(60.0 / 60.0 / dt)
    lag = lo + int(np.argmax(ac[lo:hi]))
    # 抛物线细化
    if 0 < lag < len(ac) - 1:
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
        off = 0.5 * (a - c) / (a - 2 * b + c + 1e-9)
        lag = lag + off
    period = lag * dt
    bpm = 60.0 / period
    # 相位：把包络按周期折叠，取能量最大的相位
    best, best_s = 0.0, -1.0
    for ph in np.arange(0.0, period, 0.005):
        idx = np.arange(ph, t[-1], period)
        ii = np.searchsorted(t, idx).clip(0, len(env) - 1)
        s = float(env[ii].mean())
        if s > best_s:
            best_s, best = s, ph
    return bpm, period, best


def main():
    t, env = onset_env(WAV)
    bpm, period, phase = estimate(t, env)
    beats = list(np.arange(phase, t[-1] + 1e-6, period))
    print("BPM %.2f  period %.4f s  phase %.3f s  beats %d"
          % (bpm, period, phase, len(beats)))
    json.dump(dict(bpm=round(bpm, 2), period=round(period, 4),
                   phase=round(phase, 3),
                   beats=[round(float(b), 3) for b in beats]),
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print("wrote", OUT)
    # 抽查：歌词首字离最近拍点的距离
    if len(sys.argv) > 1:
        pass


if __name__ == "__main__":
    main()
