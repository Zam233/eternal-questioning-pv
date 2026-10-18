# -*- coding: utf-8 -*-
"""Procedural middle layers: dust, smoke, sparks, falling paper.

These are what stands between the plate and the type — not frozen props but
things that are *always* moving, driven by the same camera as everything else.
"""
import numpy as np

from . import config as C
from . import tex as T
from . import camera as CAM

_cache = {}


def _rng(seed):
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def _blob(img, cx, cy, r, rgb, a):
    """Soft round dot, drawn directly into float32 (cheap)."""
    H, W = img.shape[:2]
    r = max(1.0, r)
    x0, x1 = int(cx - r * 2), int(cx + r * 2)
    y0, y1 = int(cy - r * 2), int(cy + r * 2)
    if x1 < 0 or y1 < 0 or x0 >= W or y0 >= H:
        return
    xs = np.arange(max(0, x0), min(W, x1), dtype=np.float32)
    ys = np.arange(max(0, y0), min(H, y1), dtype=np.float32)
    if xs.size == 0 or ys.size == 0:
        return
    gx = np.exp(-((xs - cx) ** 2) / (2 * r * r))[None, :]
    gy = np.exp(-((ys - cy) ** 2) / (2 * r * r))[:, None]
    m = (gy * gx * a)[:, :, None]
    sub = img[max(0, y0):min(H, y1), max(0, x0):min(W, x1)]
    sub += m * np.array(rgb, np.float32)[None, None, :]


def _seed_field(seed, n):
    key = ("f", seed, n)
    if key in _cache:
        return _cache[key]
    r = _rng(seed)
    f = dict(
        x0=r.random(n), y0=r.random(n), sp=r.normal(0, 1, n),
        sz=r.uniform(0.4, 1.0, n), ph=r.uniform(0, 6.28, n),
        life=r.uniform(0.3, 1.0, n),
    )
    _cache[key] = f
    return f


# ---------------------------------------------------------------- layers
def dust(img, L, cam, st, u):
    n = int(L.get("count", 90))
    f = _seed_field(L.get("seed", 1), n)
    s, ox, oy, roll = CAM.layer_xform(st, L.get("z", 0.5))
    spd = float(L.get("speed", 0.02))
    col = L.get("color", (210, 198, 176))
    base_a = float(L.get("alpha", 0.5))
    for i in range(n):
        x = (f["x0"][i] + f["sp"][i] * u * spd * 6 + ox) % 1.0
        y = (f["y0"][i] - u * spd * (0.4 + f["life"][i]) + oy) % 1.0
        tw = 0.55 + 0.45 * np.sin(u * 6.2 + f["ph"][i])
        a = base_a * f["life"][i] * tw * min(1.0, u * 8)
        _blob(img, x * C.W, y * C.H, (1.2 + 2.4 * f["sz"][i]) * L.get("scale", 1.0),
              col, a)


def smoke(img, L, cam, st, u):
    """Low-frequency drifting blotches, drawn with a coarse noise field."""
    n = int(L.get("count", 16))
    f = _seed_field(L.get("seed", 2), n)
    s, ox, oy, roll = CAM.layer_xform(st, L.get("z", 0.6))
    col = L.get("color", (180, 172, 160))
    base_a = float(L.get("alpha", 0.35))
    for i in range(n):
        x = (f["x0"][i] + u * 0.10 * (0.5 + f["life"][i]) + ox) % 1.0
        y = (f["y0"][i] - u * 0.05 * f["life"][i] + oy) % 1.0
        r = (60 + 150 * f["sz"][i]) * L.get("scale", 1.0)
        a = base_a * (0.4 + 0.6 * np.sin(u * 2.1 + f["ph"][i]) ** 2)
        _blob(img, x * C.W, y * C.H, r, col, a * 0.22)


def sparks(img, L, cam, st, u):
    n = int(L.get("count", 60))
    f = _seed_field(L.get("seed", 3), n)
    s, ox, oy, roll = CAM.layer_xform(st, L.get("z", 0.35))
    col = L.get("color", (255, 186, 120))
    base_a = float(L.get("alpha", 0.9))
    rise = float(L.get("rise", 0.55))
    for i in range(n):
        t = (u * (0.6 + f["life"][i]) + f["ph"][i] * 0.1) % 1.0
        x = (f["x0"][i] + f["sp"][i] * 0.03 + ox) % 1.0
        y = (1.0 - t * rise + oy) % 1.0
        a = base_a * (1.0 - t) ** 1.6 * min(1.0, u * 6)
        if a <= 0.01:
            continue
        _blob(img, x * C.W, y * C.H, 1.0 + 1.8 * f["sz"][i], col, a)


def paper(img, L, cam, st, u):
    """Few small paper flakes drifting down and turning."""
    n = int(L.get("count", 8))
    f = _seed_field(L.get("seed", 4), n)
    s, ox, oy, roll = CAM.layer_xform(st, L.get("z", 0.4))
    col = L.get("color", (226, 218, 198))
    base_a = float(L.get("alpha", 0.75))
    for i in range(n):
        t = (u * (0.25 + f["life"][i] * 0.3) + f["ph"][i] * 0.15) % 1.0
        x = (f["x0"][i] + np.sin(u * 3 + f["ph"][i]) * 0.02 + ox) % 1.0
        y = (t * 1.1 - 0.05 + oy) % 1.0
        w = (6 + 10 * f["sz"][i]) * s
        turn = np.sin(u * 4.5 + f["ph"][i])
        w2 = max(1.0, w * abs(turn))
        a = base_a * (1 - abs(turn) * 0.55) * min(1.0, u * 5)
        x0, y0 = int(x * C.W - w2 / 2), int(y * C.H - w / 2)
        x1, y1 = int(x0 + w2), int(y0 + w)
        H, W = img.shape[:2]
        if x1 <= 0 or y1 <= 0 or x0 >= W or y0 >= H:
            continue
        img[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] += \
            np.array(col, np.float32) * (a * 0.5)


def shaft(img, L, cam, st, u):
    """A slow light shaft sweeping across the frame."""
    ang = float(L.get("angle", -20))
    center = float(L.get("center", 0.42)) + u * float(L.get("drift", 0.12))
    bl = T.beam_layer(ang, center, float(L.get("width", 0.10)), 0.6)
    img += bl * (255 * float(L.get("amt", 0.35)))


FX = dict(dust=dust, smoke=smoke, sparks=sparks, paper=paper, shaft=shaft)


def draw(img, L, cam, st, u):
    fn = FX.get(L.get("mode"))
    if fn is None:
        return
    fn(img, L, cam, st, u)
