# -*- coding: utf-8 -*-
"""Texture / image processing. Everything is a pure function of (asset, params)."""
import os
import glob
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

from . import config as C

H, W = C.H, C.W

# ---------------------------------------------------------------- deterministic noise
def rng(seed):
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def hash01(*xs):
    h = 2166136261
    for x in xs:
        h ^= int(x * 1000) & 0xFFFFFFFF
        h = (h * 16777619) & 0xFFFFFFFF
    return (h % 100000) / 100000.0


def value_noise_1d(t, seed=0, octaves=3):
    """Smooth 1-D noise in [0,1]."""
    v = 0.0
    amp = 1.0
    tot = 0.0
    for o in range(octaves):
        f = 2 ** o
        x = t * f + hash01(seed, o) * 71.3
        a = np.floor(x)
        fpart = x - a
        s = fpart * fpart * (3 - 2 * fpart)
        n0 = hash01(seed, o, a)
        n1 = hash01(seed, o, a + 1)
        v += (n0 + (n1 - n0) * s) * amp
        tot += amp
        amp *= 0.55
    return v / tot


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return np.clip(x, a, b)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x ** 3


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_back(x, s=1.7):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


# ---------------------------------------------------------------- asset loading
_plate_cache = {}
_plate_manifest = None


def manifest():
    global _plate_manifest
    if _plate_manifest is None:
        import json
        p = os.path.join(C.MET, "manifest.json")
        try:
            _plate_manifest = json.load(open(p, encoding="utf-8"))
        except Exception:
            _plate_manifest = {}
    return _plate_manifest


FALLBACK = {
    "athens": "ruins", "dawn": "stars", "demolition": "ruins", "forest": "orrery",
    "forge": "orrery", "industry": "orrery", "ladder": "disputation", "market": "industry",
    "prison": "cathedral", "sisyphus": "ruins", "pyramid": "ruins", "memento": "ruins",
}


def assets_for(key):
    """AI 主视觉优先，其次时代卡底板，最后公版版画。"""
    out = []
    for base in (C.AI, os.path.join(os.path.dirname(C.AI), "era")):
        p = os.path.join(base, key + ".png")
        if os.path.exists(p):
            out.append(p)
            break
    d = os.path.join(C.MET, key)
    if not os.path.isdir(d) and FALLBACK.get(key):
        d = os.path.join(C.MET, FALLBACK[key])
    if os.path.isdir(d):
        for pat in ("*.jpg", "*.png", "*.jpeg"):
            out.extend(sorted(glob.glob(os.path.join(d, pat))))
    return out


def _duotone(lo, hi):
    """Map an L image through a duotone ramp."""
    lut = np.zeros((256, 3), np.uint8)
    for i in range(256):
        a = i / 255.0
        for k in range(3):
            lut[i, k] = int(lo[k] + (hi[k] - lo[k]) * (a ** 1.02))
    return lut


def plate(key, idx=0, long_side=2400, contrast=1.35, gamma=1.0, invert=False, blur=0.0,
          palette="sepia"):
    """Load + tone an engraving into the film's look. Cached."""
    ck = (key, idx, long_side, contrast, gamma, invert, blur, palette)
    if ck in _plate_cache:
        return _plate_cache[ck]
    from .scene import pal as _pal
    p = _pal(palette)
    pal_lo, pal_hi = p["lo"], p["hi"]
    files = assets_for(key)
    if files:
        f = files[idx % len(files)]
        im = Image.open(f).convert("L")
    else:
        im = procedural_plate(key, idx)
    # fit long side
    s = long_side / max(im.size)
    im = im.resize((max(2, int(im.width * s)), max(2, int(im.height * s))), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255.0
    # normalise exposure across wildly different sources
    lo, hi = np.percentile(a, 2.0), np.percentile(a, 98.0)
    a = np.clip((a - lo) / max(1e-3, hi - lo), 0.0, 1.0)
    if invert:
        a = 1.0 - a
    a = a ** gamma
    a = clamp((a - 0.5) * contrast + 0.5)
    # lift/darken to a consistent mean exposure so no plate goes near-black
    m = float(a.mean())
    target = 0.46 if not invert else 0.40
    a = np.clip(a + (target - m) * 0.92, 0.0, 1.0)
    a = a * 0.86 + 0.06
    g = (a * 255).astype(np.uint8)
    rgb = _duotone(pal_lo, pal_hi)[g]
    out = Image.fromarray(rgb, "RGB")
    if blur > 0:
        out = out.filter(ImageFilter.GaussianBlur(blur))
    _plate_cache[ck] = out
    return out


def procedural_plate(key, idx):
    """Fallback when a theme has no downloaded print: engraved hatching field."""
    n = rng(hash01(len(key), idx) * 1000)
    w, h = 1600, 1000
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    field = (np.sin(x * 0.02 + n.random() * 6) * 0.5 + np.sin(y * 0.017 - x * 0.008) * 0.5)
    hatch = np.sin((x + y) * 0.9) * 0.06
    v = field * 0.5 + 0.5 + hatch
    v = clamp(v) * 255
    return Image.fromarray(v.astype(np.uint8), "L")


# ---------------------------------------------------------------- static overlays
_stat = {}


def vignette():
    if "vig" in _stat:
        return _stat["vig"]
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (x - W / 2) / (W / 2)
    ny = (y - H / 2) / (H / 2)
    r = np.sqrt(nx ** 2 * 0.92 + ny ** 2 * 1.05)
    v = clamp(1.12 - 0.62 * r ** 1.6, 0.17, 1.0)
    _stat["vig"] = v[:, :, None].astype(np.float32)
    return _stat["vig"]


def scanlines(period=4, amp=0.055):
    key = ("scan", period, amp)
    if key in _stat:
        return _stat[key]
    y = np.arange(H).astype(np.float32)
    v = 1.0 - amp * (0.5 + 0.5 * np.cos(2 * np.pi * y / period))
    _stat[key] = v[:, None, None].astype(np.float32)
    return _stat[key]


def grain_tiles(n=10, seed=7):
    if "grain" in _stat:
        return _stat["grain"]
    r = rng(seed)
    tiles = []
    for i in range(n):
        g = r.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        g = np.repeat(np.repeat(g, 2, axis=0), 2, axis=1)[:H, :W]
        tiles.append(g[:, :, None])
    _stat["grain"] = tiles
    return tiles


def paper_tile(seed=3, scale=1.0):
    """Low-frequency blotchy paper/decay texture, additive."""
    key = ("paper", seed, scale)
    if key in _stat:
        return _stat[key]
    r = rng(seed)
    small = r.normal(0, 1, (H // 24, W // 24)).astype(np.float32)
    big = np.asarray(
        Image.fromarray(((small - small.min()) / (np.ptp(small) + 1e-6) * 255).astype(np.uint8), "L")
        .resize((W, H), Image.BICUBIC)
    ).astype(np.float32) / 255.0
    big = (big - 0.5)[:, :, None]
    _stat[key] = big
    return _stat[key]


# ---------------------------------------------------------------- light beams
def beam_layer(angle=-18.0, center=0.42, width=0.16, softness=0.55, gain=1.0):
    """A soft bright band crossing the frame at `angle` degrees."""
    key = ("beam", round(angle, 1), round(center, 3), round(width, 3), round(softness, 3))
    if key in _stat:
        base = _stat[key]
    else:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        a = np.deg2rad(angle)
        d = (x - W / 2) * np.sin(a) + (y - H / 2) * np.cos(a)
        d = d / H - (center - 0.5)
        g = np.exp(-(d ** 2) / (2 * (width ** 2)))
        base = g[:, :, None].astype(np.float32)
        _stat[key] = base
    return base * gain


# ---------------------------------------------------------------- mosaic (tesserae)
def mosaicize(im, cell=8, jitter=0.22, seed=0):
    """Tile the image into stone tesserae with grout gaps."""
    r = rng(seed)
    w, h = im.size
    cw, ch = max(2, w // cell), max(2, h // cell)
    small = im.resize((cw, ch), Image.BILINEAR)
    back = small.resize((w, h), Image.NEAREST)
    a = np.asarray(back).astype(np.float32)
    # per-tessera brightness jitter (blocky, aligned to the grid)
    jm = r.normal(0, 1, (ch, cw)).astype(np.float32) * (10 * jitter) + 128
    jm = np.asarray(
        Image.fromarray(np.clip(jm, 0, 255).astype(np.uint8), "L").resize((w, h), Image.NEAREST)
    ).astype(np.float32)
    a = np.clip(a + (jm[:, :, None] - 128.0) * 1.6, 0, 255)
    # grout: thin gaps on the tessera grid
    a[(np.arange(h) % cell) == 0, :, :] *= 0.55
    a[:, (np.arange(w) % cell) == 0, :] *= 0.55
    # restore structure lost to quantisation
    a = np.clip((a - 128.0) * 1.28 + 128.0, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGB")


# ---------------------------------------------------------------- glitch
def glitch(arr, amt, seed=0, tear=0.0):
    """Horizontal slice displacement + optional channel split. arr: float32 HxWx3 0..255."""
    if amt <= 0.001:
        return arr
    r = rng(seed)
    out = arr.copy()
    n = int(2 + 10 * amt)
    for _ in range(n):
        y = int(r.integers(0, H - 2))
        h = int(r.integers(3, max(4, int(8 + 90 * amt))))
        h = min(h, H - y)
        dx = int(r.normal(0, 12 + 120 * amt))
        if dx == 0:
            continue
        out[y:y + h] = np.roll(out[y:y + h], dx, axis=1)
        if r.random() < 0.28 * amt:
            out[y:y + h] *= float(r.uniform(0.45, 1.5))
    if amt > 0.58:
        s = int(1 + 7 * amt)
        out[:, :, 0] = np.roll(out[:, :, 0], s, axis=1)
        out[:, :, 2] = np.roll(out[:, :, 2], -s, axis=1)
    if tear > 0.01:
        y0 = int(H * (0.15 + 0.7 * r.random()))
        hh = int(H * tear * 0.4)
        out[y0:y0 + hh] = np.flipud(out[y0:y0 + hh])
    return out
