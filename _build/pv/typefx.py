# -*- coding: utf-8 -*-
"""Typography: glyph sprites, per-character animation, lyric strip."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from . import config as C

_font_cache = {}
_sprite_cache = {}


def font(path, size, weight=None):
    key = (path, size, weight)
    if key in _font_cache:
        return _font_cache[key]
    f = ImageFont.truetype(path, size)
    if weight:
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    _font_cache[key] = f
    return f


class Sprite:
    """A rendered piece of type, ready to be composited with a transform."""

    __slots__ = ("img", "w", "h", "rgb", "a", "glow")

    def __init__(self, img, glow_px=0):
        self.img = img
        self.w, self.h = img.size
        arr = np.asarray(img).astype(np.float32)
        self.rgb = arr[:, :, :3]
        self.a = arr[:, :, 3] / 255.0
        if glow_px > 0:
            ga = img.split()[3].filter(ImageFilter.GaussianBlur(glow_px))
            self.glow = np.asarray(ga).astype(np.float32) / 255.0
        else:
            self.glow = None


def text_sprite(text, size, color=C.CHALK, weight="Black", path=None, tracking=0.0,
                glow=0.0, halo=0, line_spacing=1.0, align="center", vertical=False):
    """Render a whole string as one RGBA sprite (cached)."""
    path = path or C.F_SERIF
    color = tuple(color) if isinstance(color, (list, tuple)) else color
    key = ("txt", text, size, color, weight, tracking, glow, halo, line_spacing, align, vertical)
    if key in _sprite_cache:
        return _sprite_cache[key]
    f = font(path, size, weight)
    chars = list(text)
    if vertical:
        pad = int(size * 0.6 + halo * 3 + glow * 3) + 8
        adv = int(size * (1.0 + tracking))
        w = int(size * 1.35) + pad * 2
        h = adv * max(1, len(chars)) + pad * 2
    else:
        advs = [int(f.getlength(ch) + size * tracking) for ch in chars]
        pad = int(size * 0.5 + halo * 3 + glow * 3) + 8
        w = int(sum(advs) + pad * 2)
        h = int(size * 1.45 + pad * 2)
    img = Image.new("RGBA", (max(16, w), max(16, h)), (color[0], color[1], color[2], 0))
    d = ImageDraw.Draw(img)
    if vertical:
        y = pad
        adv = int(size * (1.0 + tracking))
        for ch in chars:
            d.text((w // 2, y), ch, font=f, fill=(color[0], color[1], color[2], 255),
                   anchor="ma", stroke_width=halo, stroke_fill=(0, 0, 0, 190))
            y += adv
        img = img.crop(img.getbbox()) if img.getbbox() else img
    else:
        x = pad
        for ch, a in zip(chars, advs):
            d.text((x, pad), ch, font=f, fill=(color[0], color[1], color[2], 255),
                   anchor="la", stroke_width=halo, stroke_fill=(0, 0, 0, 190))
            x += a
        bb = img.getbbox()
        if bb:
            img = img.crop(bb)
    sp = Sprite(img, glow_px=glow)
    _sprite_cache[key] = sp
    return sp


def char_sprites(text, size, color=C.CHALK, weight="Black", path=None, tracking=0.0,
                 glow=0.0, halo=0):
    """One sprite per character, plus advances, for staggered animation."""
    path = path or C.F_SERIF
    color = tuple(color) if isinstance(color, (list, tuple)) else color
    key = ("chars", text, size, color, weight, tracking, glow, halo, path)
    if key in _sprite_cache:
        return _sprite_cache[key]
    f = font(path, size)
    out = []
    for ch in list(text):
        sp = text_sprite(ch, size, color=color, weight=weight, path=path, tracking=0.0,
                         glow=glow, halo=halo)
        adv = int(f.getlength(ch) + size * tracking)
        out.append((sp, adv))
    _sprite_cache[key] = out
    return out


# ------------------------------------------------------------------ compositing
def put(base, sp, cx, cy, scale=1.0, alpha=1.0, rot=0.0, glow_amt=0.0,
        glow_color=(255, 240, 210), wipe=None, wipe_soft=0.12):
    """Composite sprite centred at (cx, cy) onto float32 (H,W,3) base, in place."""
    if alpha <= 0.003:
        return
    img = sp.img
    rgb = sp.rgb
    a = sp.a
    w_orig = sp.w
    w = sp.w
    if wipe is not None:
        cut = int(np.clip(wipe, 0, 1) * (w + 1))
        if cut <= 0:
            return
        img = img.crop((0, 0, cut, sp.h))
        rgb = rgb[:, :cut]
        a = a[:, :cut]
        w = cut
    if scale != 1.0 or rot != 0.0:
        nw = max(1, int(w * scale))
        nh = max(1, int(sp.h * scale))
        im2 = img.resize((nw, nh), Image.LANCZOS)
        if rot:
            im2 = im2.rotate(rot, resample=Image.BICUBIC, expand=True)
        arr = np.asarray(im2).astype(np.float32)
        rgb = arr[:, :, :3]
        a = arr[:, :, 3] / 255.0
        w, h = im2.size
    else:
        h = sp.h
    if glow_amt > 0 and sp.glow is not None:
        gsrc = sp.glow[:a.shape[0], :a.shape[1]]
        if scale != 1.0 and gsrc.shape[:2] != a.shape[:2]:
            gsrc = np.asarray(
                Image.fromarray((gsrc * 255).astype(np.uint8)).resize((a.shape[1], a.shape[0]), Image.BILINEAR)
            ).astype(np.float32) / 255.0
        x0 = int(cx - w / 2)
        y0 = int(cy - h / 2)
        _add_glow(base, gsrc * (glow_amt * alpha), x0, y0, glow_color)
    if wipe is not None:
        x0 = int(cx - w_orig / 2)
    else:
        x0 = int(cx - w / 2)
    y0 = int(cy - h / 2)
    _blend(base, rgb, a * alpha, x0, y0)


def _blend(base, rgb, a, x0, y0):
    H, W = base.shape[:2]
    h, w = a.shape[:2]
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    dx1, dy1 = min(W, x0 + w), min(H, y0 + h)
    if dx1 <= dx0 or dy1 <= dy0:
        return
    aw = a[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)][:, :, None]
    rw = rgb[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)]
    dst = base[dy0:dy1, dx0:dx1]
    np.copyto(dst, dst * (1.0 - aw) + rw * aw)


def _add_glow(base, g, x0, y0, color):
    H, W = base.shape[:2]
    h, w = g.shape[:2]
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    dx1, dy1 = min(W, x0 + w), min(H, y0 + h)
    if dx1 <= dx0 or dy1 <= dy0:
        return
    gw = g[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)][:, :, None]
    col = np.array(color, np.float32)[None, None, :]
    base[dy0:dy1, dx0:dx1] += gw * col * 0.85


def put_shadow(base, sp, cx, cy, scale=1.0, alpha=1.0, dx=8, dy=10, blur=0.9,
               color=(6, 5, 4)):
    """Soft dark drop shadow from the sprite's alpha, for readability."""
    if sp.glow is None:
        ga = sp.img.split()[3].filter(ImageFilter.GaussianBlur(max(1.0, sp.w * 0.012)))
        g = np.asarray(ga).astype(np.float32) / 255.0
    else:
        g = sp.glow
    if scale != 1.0:
        nw = max(1, int(sp.w * scale))
        nh = max(1, int(sp.h * scale))
        g = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((nw, nh), Image.BILINEAR)
                       ).astype(np.float32) / 255.0
    else:
        nw, nh = sp.w, sp.h
    g = g * alpha * blur
    x0 = int(cx - nw / 2 + dx)
    y0 = int(cy - nh / 2 + dy)
    Hh, Ww = base.shape[:2]
    sy0, sx0 = max(0, -y0), max(0, -x0)
    dy0, dx0 = max(0, y0), max(0, x0)
    dy1, dx1 = min(Hh, y0 + g.shape[0]), min(Ww, x0 + g.shape[1])
    if dx1 <= dx0 or dy1 <= dy0:
        return
    gw = g[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)][:, :, None]
    base[dy0:dy1, dx0:dx1] *= (1.0 - 0.85 * gw)


def measure(sp, scale=1.0):
    return sp.w * scale, sp.h * scale


# ------------------------------------------------------------------ lyric strip
def lyric_pair(line, size=44, hi=C.CHALK, lo=(176, 166, 148)):
    """Return (dim_sprite, bright_sprite) for the bottom lyric line."""
    key = ("lyr", line, size)
    if key in _sprite_cache:
        return _sprite_cache[key]
    dim = text_sprite(line, size, color=lo, weight="Medium", path=C.F_SERIF,
                      tracking=0.06, halo=1)
    bright = text_sprite(line, size, color=hi, weight="Medium", path=C.F_SERIF,
                         tracking=0.06, halo=1)
    _sprite_cache[key] = (dim, bright)
    return dim, bright
