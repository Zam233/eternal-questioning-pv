# -*- coding: utf-8 -*-
"""Crude vocal/onset sanity check: RMS envelope + spectral flux in a window."""
import sys, wave, numpy as np

path = '_audio_mono.wav'
w = wave.open(path, 'rb')
sr = w.getframerate(); n = w.getnframes(); ch = w.getnchannels(); sw = w.getsampwidth()
print('wav', sr, ch, sw, n / sr, 's')
t0 = float(sys.argv[1]) if len(sys.argv) > 1 else 226.0
t1 = float(sys.argv[2]) if len(sys.argv) > 2 else 242.0
a = int(t0 * sr); b = int(t1 * sr)
w.setpos(a)
raw = w.readframes(b - a)
x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
if ch > 1:
    x = x.reshape(-1, ch).mean(axis=1)
hop = int(0.05 * sr)
win = hop * 2
frames = []
for i in range(0, len(x) - win, hop):
    seg = x[i:i + win]
    frames.append((t0 + i / sr, float(np.sqrt((seg ** 2).mean()))))
fr = np.array([f[1] for f in frames])
db = 20 * np.log10(fr + 1e-6)
print('db min/max', db.min().round(1), db.max().round(1))
for (tt, r), d in zip(frames, db):
    bar = '#' * int(max(0, (d - db.min()) / max(1e-6, db.max() - db.min()) * 50))
    print('%7.2f %6.1f %s' % (tt, d, bar))
