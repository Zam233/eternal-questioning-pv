# -*- coding: utf-8 -*-
"""Scene assembly: one frame = pure function of t.

A SHOT holds one camera for a whole phrase; the TYPE changes inside it.
Text behaviour lives in block.py, camera in motion.py, transitions in trans.py.
"""
import json
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config as C
from . import tex as T
from . import typefx as X
from . import block as B
from . import motion as M
from . import trans as TR

# ------------------------------------------------------------------ palettes
PALETTES = {
    "sepia": dict(lo=(14, 12, 10), hi=(222, 210, 186)),
    "rust":  dict(lo=(18, 9, 7),   hi=(214, 148, 112)),
    "steel": dict(lo=(9, 12, 17),  hi=(176, 198, 214)),
    "gold":  dict(lo=(20, 14, 6),  hi=(226, 202, 138)),
    "cold":  dict(lo=(10, 11, 12), hi=(196, 198, 194)),
    "blood": dict(lo=(16, 6, 6),   hi=(196, 106, 92)),
    "ivory": dict(lo=(24, 22, 18), hi=(238, 232, 218)),
    "ash":   dict(lo=(12, 12, 12), hi=(206, 206, 200)),
}


def pal(name):
    return PALETTES.get(name or "sepia", PALETTES["sepia"])


# ------------------------------------------------------------------ plate windows
_plate_var = {}
_PLATE_CAP = 10


def plate_variant(key, idx, mode="plate", palette="sepia"):
    ck = (key, idx, mode, palette)
    if ck in _plate_var:
        _plate_var[ck] = _plate_var.pop(ck)
        return _plate_var[ck]

    long_side = 2400
    if mode == "mosaic":
        base = T.plate(key, idx, long_side=1900, contrast=1.20, gamma=1.0, palette=palette)
        mos = T.mosaicize(base, cell=7, jitter=0.18, seed=idx + 11)
        im = Image.blend(base, mos, 0.50)
    elif mode == "ink":
        im = T.plate(key, idx, long_side=long_side, contrast=1.15, gamma=1.15, invert=True,
                     palette=palette)
    elif mode == "ghost":
        im = T.plate(key, idx, long_side=1600, contrast=0.95, gamma=1.05, blur=2.2, palette=palette)
    elif mode == "light":
        im = T.plate(key, idx, long_side=long_side, contrast=0.72, gamma=1.30, palette=palette)
    else:
        im = T.plate(key, idx, long_side=long_side, contrast=1.18, gamma=0.98, palette=palette)

    s = max(C.W * 1.45 / im.width, C.H * 1.45 / im.height)
    im = im.resize((max(C.W, int(im.width * s)), max(C.H, int(im.height * s))), Image.LANCZOS)
    _plate_var[ck] = im
    while len(_plate_var) > _PLATE_CAP:
        _plate_var.pop(next(iter(_plate_var)))
    return im


def window(im, cx, cy, zoom, rot=0.0):
    w, h = im.width, im.height
    vw = min(C.W / max(0.2, zoom), w)
    vh = min(C.H / max(0.2, zoom), h)
    x0 = np.clip(cx * w - vw / 2, 0, w - vw)
    y0 = np.clip(cy * h - vh / 2, 0, h - vh)
    crop = im.crop((int(x0), int(y0), int(x0 + vw), int(y0 + vh)))
    if abs(rot) > 0.12:
        crop = crop.resize((C.W, C.H), Image.BILINEAR).rotate(rot, resample=Image.BILINEAR)
        crop = crop.crop(((crop.width - C.W) // 2, (crop.height - C.H) // 2,
                          (crop.width - C.W) // 2 + C.W, (crop.height - C.H) // 2 + C.H))
    elif crop.size != (C.W, C.H):
        crop = crop.resize((C.W, C.H), Image.BILINEAR)
    return np.asarray(crop).astype(np.float32)


# ------------------------------------------------------------------ small text
def small(dst, txt, x, y, size=26, color=(150, 140, 122), weight="Regular",
          path=None, anchor="la", tracking=0.10, alpha=1.0):
    if not txt or alpha <= 0.004:
        return
    sp = X.text_sprite(txt, size, color=color, weight=weight, path=path or C.F_SERIF,
                       tracking=tracking, halo=0)
    w, h = sp.w, sp.h
    if anchor[0] == "c":
        x -= w / 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "c":
        y -= h / 2
    elif anchor[1] == "b":
        y -= h
    X._blend(dst, sp.rgb, sp.a * alpha, int(x), int(y))


# ------------------------------------------------------------------ scrims
_foot = {}


def foot_scrim(img, top=0.70, strength=0.80):
    key = (round(top, 3), round(strength, 3))
    m = _foot.get(key)
    if m is None:
        y = np.linspace(0.0, 1.0, C.H, dtype=np.float32)
        band = np.clip((y - top) / max(1e-3, 1 - top), 0, 1) ** 1.5
        m = (1.0 - strength * band)[:, None, None].astype(np.float32)
        _foot[key] = m
    img *= m


def head_scrim(img, bottom=0.16, strength=0.66):
    key = ("h", round(bottom, 3), round(strength, 3))
    m = _foot.get(key)
    if m is None:
        y = np.linspace(0.0, 1.0, C.H, dtype=np.float32)
        band = np.clip((bottom - y) / max(1e-3, bottom), 0, 1) ** 1.4
        m = (1.0 - strength * band)[:, None, None].astype(np.float32)
        _foot[key] = m
    img *= m


def band_scrim(img, center, width, strength):
    key = ("b", int(center), int(width), round(strength, 2))
    m = _foot.get(key)
    if m is None:
        y = np.arange(C.H, dtype=np.float32)[:, None]
        band = np.exp(-(((y - center) / (width + 1e-6)) ** 2))
        m = (1.0 - strength * band)[:, :, None].astype(np.float32)
        _foot[key] = m
    img *= m


# ------------------------------------------------------------------ occlusion
def foreground(img, key, idx, mode, palette, side, strength=0.85, band=0.30,
               cx=0.5, cy=0.5, zoom=1.0):
    if strength <= 0.02 or side in (None, "", "none"):
        return
    im = plate_variant(key, idx, mode, palette)
    win = window(im, cx, cy, zoom)
    lum = win.mean(axis=2) / 255.0
    a = np.clip((0.60 - lum) / 0.60, 0, 1) ** 1.5 * strength
    mask = np.zeros((C.H, C.W), np.float32)
    if side == "left":
        mask[:, :int(C.W * band)] = 1.0
    elif side == "right":
        mask[:, int(C.W * (1 - band)):] = 1.0
    elif side == "bottom":
        mask[int(C.H * (1 - band)):, :] = 1.0
    elif side == "top":
        mask[:int(C.H * band), :] = 1.0
    a = (a * mask)[:, :, None]
    np.copyto(img, img * (1 - a) + win * 0.72 * a)


# ------------------------------------------------------------------ shot render
def base_ink(u, seed=0):
    y, x = np.mgrid[0:C.H, 0:C.W].astype(np.float32)
    g = 0.5 + 0.5 * np.sin(x / C.W * 2.2 + u * 0.9 + seed)
    v = (10 + 9 * g)[:, :, None]
    out = np.repeat(v, 3, axis=2)
    out[:, :, 2] *= 1.06
    return out


def render_shot(sh, t):
    t0, t1 = sh["t0"], sh["t1"]
    d = max(1e-3, t1 - t0)
    u = float(np.clip((t - t0) / d, 0, 1))
    seed = sh.get("seed", int(t0 * 13) & 0xFFFF)

    if sh.get("layers"):
        from . import puppet as PUP
        img = PUP.compose(sh, t)
        if sh.get("invert"):
            img = 255.0 - img
            img = img * 0.80 + 52.0
        if not sh.get("invert"):
            head_scrim(img, sh.get("head_top", 0.16), sh.get("head_amt", 0.55))
            foot_scrim(img, sh.get("foot_top", 0.76), sh.get("foot_amt", 0.62))
        _meta(img, sh, u, t)
        return img

    key, idx = sh.get("asset", ["ruins", 0])
    mode = sh.get("mode", "plate")
    palette = sh.get("palette", "sepia")

    zoom, cx, cy, rot = M.apply(sh, u)
    pa = sh.get("plate_alpha", 1.0)
    if pa > 0.01:
        img = window(plate_variant(key, idx, mode, palette), cx, cy, zoom, rot)
        if pa < 0.999:
            img *= pa
    else:
        img = base_ink(u, seed)

    if sh.get("invert"):
        img = 255.0 - img
        # a bleached paper page, not a photo negative
        img = img * 0.80 + 52.0

    img += T.paper_tile(seed % 5 + 1) * 12.0
    beam = sh.get("beam")
    if beam:
        bl = T.beam_layer(beam.get("angle", -18), beam.get("center", 0.42),
                          beam.get("width", 0.16), beam.get("softness", 0.6))
        amt = beam.get("amt", 1.0)
        if beam.get("drift"):
            bl = np.roll(bl, int(beam["drift"] * 520 * (u - 0.5) * 2), axis=1)
        img += bl * (255 * 0.20 * amt)

    ghost = sh.get("ghost")
    if ghost:
        sp = X.text_sprite(ghost["text"], ghost.get("size", 620), color=(52, 47, 40),
                           weight="Black", tracking=ghost.get("tracking", 0.08))
        px = 0.5 + ghost.get("dx", 0.0) * (u - 0.5) * 2
        py = 0.5 + ghost.get("dy", 0.0) * (u - 0.5) * 2
        X.put(img, sp, C.W * px, C.H * py, scale=ghost.get("scale", 1.0),
              alpha=ghost.get("alpha", 0.5) * min(1.0, u * 6))

    head_scrim(img, sh.get("head_top", 0.16), 0.0 if sh.get("invert") else sh.get("head_amt", 0.62))
    foot_scrim(img, sh.get("foot_top", 0.74), 0.0 if sh.get("invert") else sh.get("foot_amt", 0.72))
    if sh.get("scrim"):
        img *= (1.0 - sh["scrim"])

    # ---- type blocks
    for cue in sh.get("cues", []):
        if cue.get("scrim_y"):
            band_scrim(img, cue["scrim_y"], cue.get("scrim_w", C.H * 0.22), cue["scrim_y_amt"])
        B.draw(img, cue, t)

    # ---- foreground occlusion
    fg = sh.get("fg")
    if fg:
        foreground(img, key, idx, mode, palette, fg.get("side", "left"),
                   fg.get("strength", 0.85), fg.get("band", 0.30), cx, cy, zoom)

    _meta(img, sh, u, t)
    return img


def _meta(img, sh, u, t):
    """Book-plate meta: number, concept annotation, credits.

    v17：整片不再在画面里打 PLATE 编号与拉丁小标（hide_meta），
    这些字段只留在 shots.json 里当镜头标识与审稿用。
    """
    if sh.get("hide_meta"):
        return
    cap = sh.get("caption")
    if cap and (cap.get("no") or cap.get("txt")):
        a = T.clamp((u - 0.04) * 5.0) * 0.92
        small(img, cap.get("no", ""), C.SAFE, 74, size=24, color=(196, 168, 122),
              weight="Bold", tracking=0.30, alpha=a)
        small(img, cap.get("txt", ""), C.SAFE, 108, size=25, color=(146, 136, 120),
              weight="Regular", tracking=0.14, alpha=a * 0.9)
        small(img, cap.get("yr", ""), C.W - C.SAFE, 74, size=22, color=(120, 112, 96),
              weight="Regular", tracking=0.26, alpha=a * 0.8, anchor="ra")

    anno = sh.get("anno")
    if anno and (anno.get("t") or anno.get("latin")):
        a = T.clamp((u - 0.02) * 4.0) * 0.95
        pos = sh.get("anno_pos", "br")
        ax = C.SAFE if "l" in pos else C.W - C.SAFE
        ay = C.H - 150 if "b" in pos else 176
        an = "la" if "l" in pos else "ra"
        small(img, anno.get("t", ""), ax, ay, size=32, color=(206, 184, 142),
              weight="SemiBold", tracking=0.16, alpha=a * 0.9, anchor=an)
        small(img, anno.get("latin", ""), ax, ay + 44, size=21, color=(138, 128, 112),
              weight="Regular", tracking=0.40, alpha=a * 0.85, anchor=an)

    cr = sh.get("credits")
    if cr:
        a = T.clamp((t - cr["t0"]) / 0.8) * T.clamp(1.0 - (t - cr["t1"]) / 0.6)
        if a > 0.01:
            y = cr.get("y", 0.70) * C.H
            for i, line in enumerate(cr["lines"]):
                small(img, line, cr.get("x", 0.5) * C.W, y + i * cr.get("gap", 58),
                      size=cr.get("size", 28), color=(206, 198, 180),
                      weight="Regular", tracking=0.16, alpha=a * 0.78,
                      anchor=cr.get("anchor", "ca"))


# ------------------------------------------------------------------ post
def halation(arr, amt):
    """高光溢光：亮部晕开一层暖光，是"现代"后期里最便宜的一档质感。"""
    if amt <= 0.01:
        return arr
    lum = arr.max(axis=2)
    m = np.clip((lum - 185.0) / 70.0, 0.0, 1.0)
    if float(m.max()) < 0.02:
        return arr
    from PIL import Image, ImageFilter
    mi = Image.fromarray((m * 255.0).astype(np.uint8)).filter(ImageFilter.GaussianBlur(16))
    soft = np.asarray(mi).astype(np.float32) / 255.0
    warm = np.array([255.0, 219.0, 176.0], np.float32)
    return arr + (soft[..., None] ** 1.15) * warm * (0.5 * amt)


_EDGE = {}


def edge_mask(k, W=None, H=None):
    """fxd 的"从四边压进来"：k=0 无，k=1 只留中央一条软亮带。"""
    k = float(max(0.0, min(1.0, k)))
    key = int(k * 40)
    m = _EDGE.get(key)
    if m is None:
        kk = key / 40.0
        yy, xx = np.mgrid[0:C.H, 0:C.W].astype(np.float32)
        d = np.maximum(np.abs(xx / C.W - 0.5), np.abs(yy / C.H - 0.5)) * 2.0
        thr = 1.0 - kk * 0.95
        band = np.clip((d - thr) / 0.18, 0.0, 1.0)
        m = (1.0 - 0.96 * band)[..., None].astype(np.float32)
        _EDGE[key] = m
    return m


def post(img, sh, t, u):
    seed = sh.get("seed", 7) + int(t * C.FPS)
    p = sh.get("post") or {}
    scan_k = float(p.get("scan", 1.0))
    glitch_k = float(p.get("glitch", 1.0))
    bloom_k = float(p.get("bloom", 0.0))
    g = sh.get("glitch", [0.0, 0.0])
    amt = g[0] + (g[1] - g[0]) * T.ease_io(u)
    amt += 0.08 * T.value_noise_1d(t * 0.55, seed=sh.get("seed", 3))
    if u < 0.02 or u > 0.985:
        amt *= 0.3
    amt = min(amt * glitch_k, 1.6)
    tear = sh.get("tear", 0.0) * amt
    gscale = (6.5 + 5.5 * amt) * sh.get("grain", 1.0)

    from . import gpu as G
    if G.cp() is not None:
        try:
            gt = T.grain_tiles()
            out = G.post(img, sh, t, seed, amt, tear, gscale,
                         G._up("vig", T.vignette()),
                         G._up("scan", T.scanlines(4, 0.05 * scan_k)),
                         G._up("gt%d" % (seed % len(gt)), gt[seed % len(gt)]))
            if out is not None:
                out = halation(out, bloom_k)
                e0 = float(p.get("edge0", 0.0)); e1 = float(p.get("edge1", 0.0))
                if e0 or e1:
                    out = out * edge_mask(e0 + (e1 - e0) * T.ease_io(u))
                sc = p.get("scratch")
                if sc:
                    x = int(float(sc) * C.W)
                    warm = np.array([205.0, 196.0, 178.0], np.float32)
                    out[:, x:x + 2] = out[:, x:x + 2] * 0.55 + warm * 0.45 * 0.55
                return out
        except Exception:
            pass

    arr = T.glitch(img, amt, seed=seed, tear=tear)
    arr = arr * T.scanlines(4, 0.05 * scan_k)
    gt = T.grain_tiles()
    arr = arr + gt[seed % len(gt)] * gscale
    arr = arr * T.vignette()
    arr = halation(arr, bloom_k)
    e0 = float(p.get("edge0", 0.0)); e1 = float(p.get("edge1", 0.0))
    if e0 or e1:
        arr = arr * edge_mask(e0 + (e1 - e0) * T.ease_io(u))
    sc = p.get("scratch")
    if sc:
        x = int(float(sc) * C.W)
        warm = np.array([205.0, 196.0, 178.0], np.float32)
        arr[:, x:x + 2] = arr[:, x:x + 2] * 0.55 + warm * 0.45 * 0.55
    return arr


def finish(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def render_frame(sh, t):
    img = render_shot(sh, t)
    u = (t - sh["t0"]) / max(1e-3, sh["t1"] - sh["t0"])
    arr = post(img, sh, t, u)
    arr = TR.apply(arr, sh, t - sh["t0"])
    return np.clip(arr, 0, 255)
