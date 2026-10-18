# -*- coding: utf-8 -*-
"""Type blocks: one function per typographic behaviour.

A cue looks like:
  {kind, text, t0, t1, words:[{t0}], layout, px, color, rot, glow, mode...}
Each glyph lands on its own sung onset; `kind` decides what else happens to it.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config as C
from . import tex as T
from . import typefx as X

# ------------------------------------------------------------------ anchors
LAYOUTS = {
    "center":    dict(x=0.500, y=0.440, s=1.00, align="c"),
    "low_center": dict(x=0.500, y=0.735, s=0.85, align="c"),
    "up_center": dict(x=0.500, y=0.235, s=0.85, align="c"),
    "low_left":  dict(x=0.300, y=0.715, s=0.60, align="l"),
    "low_right": dict(x=0.700, y=0.705, s=0.58, align="r"),
    "up_right":  dict(x=0.700, y=0.265, s=0.52, align="r"),
    "up_left":   dict(x=0.300, y=0.275, s=0.54, align="l"),
    "right_v":   dict(x=0.870, y=0.340, s=0.62, align="c"),
    "left_v":    dict(x=0.120, y=0.340, s=0.58, align="c"),
    "far_left":  dict(x=0.180, y=0.470, s=0.52, align="l"),
    "far_right": dict(x=0.830, y=0.470, s=0.52, align="r"),
    "top_left":  dict(x=0.130, y=0.165, s=0.42, align="l"),
    "bottom_right": dict(x=0.880, y=0.860, s=0.40, align="r"),
    "bottom_left": dict(x=0.140, y=0.930, s=0.90, align="l"),
}


def layout(name):
    return LAYOUTS.get(name, LAYOUTS["center"])


def fit_px(n, lname, cap=340, frac=0.46):
    L = layout(lname)
    if lname in ("center", "up_center", "low_center"):
        frac = 0.80
    w = frac * C.W / max(1, n)
    return int(min(cap, w))


# ------------------------------------------------------------------ helpers
def _clip_rect(img, cue):
    r = cue.get("clip")
    if not r:
        return img
    x0, y0, x1, y1 = [int(v) for v in r]
    mask = np.zeros(img.shape[:2], np.float32)
    mask[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = 1.0
    return img * mask[:, :, None]


def _hash(*xs):
    h = 2166136261
    for x in xs:
        h ^= int(abs(x) * 1000) & 0xFFFFFFFF
        h = (h * 16777619) & 0xFFFFFFFF
    return (h % 100000) / 100000.0


# ------------------------------------------------------------------ main entry
def draw(img, cue, t):
    """Composite one type block onto float32 (H,W,3) image, in place."""
    c0, c1 = cue["t0"], cue["t1"]
    if t < c0 - 0.06 or t > c1 + 0.55:
        return
    kind = cue.get("kind", "line")
    text = cue.get("text", "")
    if kind == "credits":
        return _credits(img, cue, t)
    if not text:
        return

    if kind == "echo":
        return _echo(img, cue, t)
    if kind == "watermark":
        return _watermark(img, cue, t)
    if kind == "dossier":
        return _dossier(img, cue, t)
    if kind in ("stamp", "skew"):
        return _stamp(img, cue, t, skew_boost=(12 if kind == "skew" else 0))
    if kind == "frame":
        return _frame(img, cue, t)
    if kind == "dots":
        return _dots(img, cue, t)
    if kind == "collide":
        return _collide(img, cue, t)
    if kind == "radial":
        return _radial(img, cue, t)
    if kind == "scan":
        return _scan(img, cue, t)
    if kind == "erode":
        return _erode(img, cue, t)
    if kind == "title3d":
        return _extrude(img, cue, t)
    if cue.get("vertical"):
        return _vertical(img, cue, t)
    return _chars(img, cue, t, kind)


# ---------------------------------------------------------------- credits
def _credits(img, cue, t):
    """片尾式制作名单：两栏（角色右对齐／姓名左对齐）、竖发丝线、
    逐行左滑入、整块收尾淡出。纯 t 的函数。"""
    rows = [r for r in (cue.get("rows") or []) if r and len(r) >= 2]
    if not rows:
        return
    W, H = C.W, C.H
    t0, t1 = float(cue["t0"]), float(cue["t1"])
    step = float(cue.get("step", 1.55))
    xr = float(cue.get("x_role", 0.452)) * W
    xn = float(cue.get("x_name", 0.474)) * W
    y0 = float(cue.get("y", 0.315)) * H
    gap = float(cue.get("gap", 0.072)) * H
    pr = int(cue.get("px_role", 27))
    pn = int(cue.get("px_name", 42))
    c_role = tuple(cue.get("c_role", (146, 136, 118)))
    c_name = tuple(cue.get("c_name", (232, 212, 176)))
    amul = float(cue.get("alpha", 1.0))
    n = len(rows)

    # 整块在收尾处淡出
    blk = T.clamp((t1 - t) / 0.85) if t > t1 - 0.85 else 1.0
    # 顶部横发丝线：从左向右画出来
    ytop = y0 - gap * 0.62
    wp = T.ease_out(T.clamp((t - t0 + 0.30) / 0.70))
    if wp > 0.01 and blk > 0.01:
        x0, x1 = int(xr - 108), int(xn + 330)
        xa = int(x0 + (x1 - x0) * wp)
        a = 0.30 * wp * blk * amul
        y = int(ytop)
        if 0 <= y < H:
            seg = img[y:y + 1, x0:max(x0 + 1, xa)]
            seg *= 1.0 - a
            seg += np.array(c_name, np.float32) * a

    for i, row in enumerate(rows):
        role, name = str(row[0]), str(row[1])
        tin = t0 + i * step
        p = T.clamp((t - tin) / 0.60)
        if p <= 0.004 or blk <= 0.004:
            continue
        e = T.ease_out(p)
        a = e * blk * amul
        dx = -26.0 * (1.0 - e)
        y = y0 + i * gap
        sp = X.text_sprite(role, pr, color=c_role, weight="Regular", tracking=0.26)
        X._blend(img, sp.rgb, sp.a * (a * 0.66), int(xr - sp.w + dx), int(y - sp.h * 0.5))
        sn = X.text_sprite(name, pn, color=c_name, weight="SemiBold", tracking=0.05)
        X._blend(img, sn.rgb, sn.a * (a * 0.92), int(xn + dx), int(y - sn.h * 0.5))

    # 落款：拉丁小标，最后一行之后出现
    shown = min(n, max(0, int((t - t0) / step) + 1))
    latin = cue.get("latin")
    if latin and shown >= n and blk > 0.01:
        la = T.clamp((t - (t0 + (n - 1) * step + 0.55)) / 0.70)
        if la > 0.01:
            ly = y0 + (n - 1) * gap + gap * 0.95
            sl = X.text_sprite(latin, int(pr * 0.82), color=c_role,
                               weight="Regular", tracking=0.62)
            X._blend(img, sl.rgb, sl.a * (la * blk * amul * 0.44),
                     int(xn), int(ly - sl.h * 0.5))

    # 竖发丝线：跟着已出现的最后一行往下长，像页边的尺
    if shown >= 1 and blk > 0.01:
        vp = T.ease_out(T.clamp((t - t0 - 0.20) / 0.70))
        x = int((xr + xn) * 0.5) - 1
        ya = y0 - gap * 0.42
        yb = y0 + (shown - 1) * gap + gap * 0.42
        a = 0.24 * vp * blk * amul
        if 0 <= x < W and ya < yb:
            col = img[int(ya):int(yb), x:x + 2]
            col *= 1.0 - a
            col += np.array(c_name, np.float32) * a


# ---------------------------------------------------------------- per-glyph
PUNCT_RE = None


def strip_punct(s):
    """Animated type never carries punctuation or spaces."""
    global PUNCT_RE
    if PUNCT_RE is None:
        import re
        PUNCT_RE = re.compile(r'[\s\u3000"\u201c\u201d\'\u2018\u2019,，.。!！?？;；:：、\u00b7]')
    return PUNCT_RE.sub("", s or "")


def _band_scrim(img, cx, cy, w, h, strength):
    """Local darkening only under the type block (R2/R5)."""
    H, W = img.shape[:2]
    x0 = max(0, int(cx - w / 2))
    x1 = min(W, int(cx + w / 2))
    y0 = max(0, int(cy - h / 2))
    y1 = min(H, int(cy + h / 2))
    if x1 <= x0 or y1 <= y0:
        return
    yy = np.arange(y0, y1, dtype=np.float32)[:, None]
    band = np.exp(-(((yy - cy) / (h * 0.55 + 1e-6)) ** 2)) * strength
    xx = np.arange(x0, x1, dtype=np.float32)[None, :]
    feath = np.clip(np.minimum(xx - x0, x1 - xx) / (w * 0.18 + 1e-6), 0, 1)
    m = (1.0 - band * feath)[:, :, None]
    img[y0:y1, x0:x1] *= m


def _chars(img, cue, t, kind):
    text = cue.get("text", "") if cue.get("raw_text") else strip_punct(cue.get("text", ""))
    if not text:
        return
    L = layout(cue.get("layout", "center"))
    n = len(text)
    justify = bool(cue.get("justify")) or kind == "band"
    band_w = float(cue.get("band", 0.78)) * C.W
    if justify:
        step = band_w / n
        px = int(min(cue.get("px") or step * 0.66, step * 0.66))
    else:
        px = cue.get("px") or fit_px(n, cue.get("layout", "center"))
    # R3: minimum legible size for anything that is read as a lyric
    if kind not in ("bleed", "quiet", "dossier", "note", "watermark") and not cue.get("bleed"):
        px = max(px, 84)
    color = cue.get("color") or C.CHALK
    track = cue.get("tracking", 0.02)
    glow = cue.get("glow", 0.5)
    rot0 = cue.get("rot", 0.0)
    t0, t1 = cue["t0"], cue["t1"]
    pout = T.clamp((t - (t1 - 0.26)) / 0.26)
    words = cue.get("words") or []

    chars = X.char_sprites(text, px, color=color, weight="Black", tracking=track, glow=glow)
    # step by the real sprite width, not the font advance: CJK ink is wider than
    # its advance, which is what used to push blocks off the frame
    steps = [max(adv, sp.w) for sp, adv in chars]
    total = sum(steps)
    if justify:
        steps = [band_w / n] * n
        total = band_w
    usable = C.W - 2 * C.SAFE - 40
    if total > usable and not (kind == "bleed" or cue.get("bleed")):
        k = usable / float(total)
        px = max(36, int(px * k))
        chars = X.char_sprites(text, px, color=color, weight="Black", tracking=track, glow=glow)
        steps = [max(adv, sp.w) for sp, adv in chars]
        total = sum(steps)
        if justify:
            steps = [usable / n] * n
            total = usable
    amul = float(cue.get("alpha", 1.0) or 1.0)

    if kind == "squash":
        sp = X.text_sprite(text, px, color=color, weight="Black", tracking=track, glow=glow)
        nw, nh = sp.w, max(4, int(sp.h * 0.38))
        im2 = sp.img.resize((nw, nh), Image.LANCZOS)
        arr = np.asarray(im2).astype(np.float32)
        pin = T.ease_out(T.clamp((t - cue["t0"]) / 0.3))
        a = pin * (1 - pout) * amul
        X._blend(img, arr[:, :, :3], arr[:, :, 3] / 255.0 * a,
                 int(L["x"] * C.W - nw / 2), int(L["y"] * C.H - nh / 2))
        return

    # anchor x
    if L["align"] == "l":
        cx = L["x"] * C.W + total / 2
    elif L["align"] == "r":
        cx = L["x"] * C.W - total / 2
    else:
        cx = L["x"] * C.W
    cy = L["y"] * C.H
    cx += float(cue.get("_cam_dx", 0.0) or 0.0) * C.W

    bleed = kind == "bleed" or cue.get("bleed")
    if not bleed:
        half = total / 2
        lo, hi = C.SAFE + half + 8, C.W - C.SAFE - half - 8
        if lo <= hi:
            cx = min(max(cx, lo), hi)
        else:
            cx = C.W / 2
    if cue.get("dy"):
        cy += cue["dy"] * C.H
    cy += float(cue.get("_cam_dy", 0.0) or 0.0) * C.H

    # ---------------- readability R1 / R2 / R4 / R7
    if cue.get("auto_color", True) and not cue.get("color"):
        H, W = img.shape[:2]
        bx0 = int(np.clip(cx - total / 2, 0, W - 1))
        bx1 = int(np.clip(cx + total / 2, 1, W))
        by0 = int(np.clip(cy - px * 0.72, 0, H - 1))
        by1 = int(np.clip(cy + px * 0.72, 1, H))
        if bx1 > bx0 and by1 > by0:
            sub = img[by0:by1, bx0:bx1]
            bl = float(sub.mean()) / 255.0
            mc = sub.reshape(-1, 3).mean(axis=0)
            hue = mc / max(1.0, float(mc.max()))
            if bl > 0.55:
                # dark type, still tinted by the plate it sits on
                color = tuple(int(np.clip(hue[i] * 60 + 22, 12, 96)) for i in range(3))
            else:
                # light type as the pale version of this plate's own colour
                color = tuple(int(np.clip(hue[i] * 108 + 132, 120, 248)) for i in range(3))
                if bl > 0.26:
                    _band_scrim(img, cx, cy, total * 1.05, px * 1.9, 0.32)
            chars = X.char_sprites(text, px, color=color, weight="Black",
                                   tracking=track, glow=glow)
            steps = [max(adv, sp.w) for sp, adv in chars]
            total = sum(steps)
            if justify:
                steps = [band_w / n] * n
                total = band_w
    shadow_dx = max(2, int(px * 0.030))
    shadow_dy = max(3, int(px * 0.035))
    shadow_blur = max(0.6, px * 0.012)

    x = cx - total / 2
    n = len(chars)
    for i, (sp, adv) in enumerate(chars):
        stp = steps[i]
        on = float(words[i]["t0"]) if i < len(words) else t0 + i * 0.06
        on = min(on, t1 - 0.22)          # every glyph gets at least 0.22 s on screen
        p = T.ease_out(T.clamp((t - on) / 0.20))
        if p <= 0.004:
            x += stp
            continue
        dx = dy = 0.0
        s = 1.0
        r = rot0
        a = p * (1.0 - pout)
        if cue.get("erase") and t > t1 - 0.26:
            rem = T.clamp((t - (t1 - 0.22 + (n - 1 - i) * (0.18 / max(1, n)))) / 0.08)
            a *= (1.0 - rem)
        u = _hash(cue.get("seed", 1), i)

        if kind == "wave":
            dy = -abs(np.sin((i * 0.9) + cue.get("phase", 0.0))) * px * 0.18
            s = 0.92 + 0.16 * u
            r = rot0 + (u - 0.5) * 4.0
            dy += (1 - p) * 30
        elif kind == "scatter":
            rr = T.rng(int(t0 * 31) + i)
            dx = rr.normal(0, px * 0.35) * (1 - p)
            dy = rr.normal(0, px * 0.30) * (1 - p)
            r = rot0 + rr.normal(0, 6) * (1 - p)
        elif kind == "fall":
            dy = (1 - p) * px * 1.2
            r = rot0 + (1 - p) * 16 * (1 if i % 2 else -1)
        elif kind == "sink":
            dy = (1 - p) * px * 0.5 + pout * px * 1.1
        elif kind == "floatup":
            dy = (1 - p) * px * 0.35 - pout * px * 1.2
        elif kind == "rise":
            dy = (1 - p) * 46
        elif kind == "punch":
            s = 1.18 - 0.18 * p
        elif kind == "ignite":
            s = 1.0
            a = p * (1 - pout)
        elif kind == "squash":
            s = 1.0
        elif kind == "shuffle":
            rr = T.rng(int(t0 * 17) + i)
            if 0.15 < (t - t0) < 0.55:
                dx = rr.normal(0, 26)
                dy = rr.normal(0, 18)
            s = 1.0
        elif kind == "tilt":
            r = rot0 + 15.0
        elif kind == "exit":
            dx = (t - t0) * C.W * 0.55
            a = p * amul

        a *= amul
        if kind == "squash":
            pass
        sc = (s, s * (0.38 if kind == "squash" else 1.0))
        if a > 0.004:
            X.put_shadow(img, sp, x + stp / 2 + dx, cy + dy, scale=sc[1] if kind == "squash" else s,
                         alpha=a * 0.90, dx=shadow_dx, dy=shadow_dy, blur=shadow_blur)
            X.put(img, sp, x + stp / 2 + dx, cy + dy,
                  scale=(s if kind != "squash" else 1.0), rot=r, alpha=a,
                  glow_amt=(1.9 * glow) if kind == "ignite" else glow * 1.4)
            if kind == "squash":
                # redraw squashed by vertical resize of a copy
                pass
        x += stp

    if kind == "strike":
        _strike(img, cue, t, cx, cy, total, px)
    if kind == "cut":
        _cut_blocks(img, cue, t)


def _strike(img, cue, t, cx, cy, total, px):
    """A line sweeps through the characters, striking them out."""
    t0, t1 = cue["t0"], cue["t1"]
    p = T.clamp((t - t0 - 0.25) / max(0.2, (t1 - t0) * 0.6))
    if p <= 0:
        return
    H, W = C.H, C.W
    x0 = int(cx - total / 2)
    x1 = int(x0 + total * p)
    y = int(cy)
    th = max(2, int(px * 0.045))
    xa, xb = max(0, x0), min(W, x1)
    if xb <= xa:
        return
    img[max(0, y - th):min(H, y + th), xa:xb] *= 0.25
    img[max(0, y - th):min(H, y + th), xa:xb] += 40


def _cut_blocks(img, cue, t):
    """Slices the whole frame into blocks and offsets them (text included)."""
    t0, t1 = cue["t0"], cue["t1"]
    p = T.clamp((t - t0 - 0.1) / 0.9)
    if p <= 0:
        return
    amp = np.sin(p * np.pi) * cue.get("cut_amp", 1.0)
    if amp < 0.02:
        return
    r = T.rng(int(t0 * 13))
    nx, ny = 4, 4
    bw, bh = C.W // nx, C.H // ny
    for gy in range(ny):
        for gx in range(nx):
            dx = int(r.normal(0, 18) * amp)
            dy = int(r.normal(0, 12) * amp)
            y0, y1 = gy * bh, (gy + 1) * bh
            x0, x1 = gx * bw, (gx + 1) * bw
            img[y0:y1, x0:x1] = np.roll(img[y0:y1, x0:x1], (dy, dx), axis=(0, 1))


# ---------------------------------------------------------------- vertical
def _vertical(img, cue, t):
    text = strip_punct(cue.get("text", ""))
    if not text:
        return
    L = layout(cue.get("layout", "right_v"))
    px = int(cue.get("px") or 126)
    track = cue.get("tracking", 0.10)
    n = len(text)
    # R6': a vertical column must fit between the safe margins — shrink, then clamp
    adv = px * (1.0 + track)
    room = C.H - 2 * C.SAFE - 20
    if adv * n > room:
        adv = room / n
        px = max(40, int(adv / (1.0 + track)))
    color = cue.get("color") or C.CHALK
    glow = cue.get("glow", 0.5)
    t0, t1 = cue["t0"], cue["t1"]
    pout = T.clamp((t - (t1 - 0.26)) / 0.26)
    words = cue.get("words") or []
    chars = X.char_sprites(text, px, color=color, weight="Black", tracking=track, glow=glow)
    adv = int(px * (1.0 + track))
    total = adv * n
    cy0 = L["y"] * C.H
    y = cy0 - total / 2
    y = min(max(y, C.SAFE + 6), C.H - C.SAFE - 6 - total)
    for i, (sp, _a) in enumerate(chars):
        on = float(words[i]["t0"]) if i < len(words) else t0 + i * 0.08
        p = T.ease_out(T.clamp((t - on) / 0.22))
        if p <= 0.004:
            y += adv
            continue
        a = p * (1 - pout)
        X.put_shadow(img, sp, L["x"] * C.W, y + adv / 2 + (1 - p) * 18,
                     alpha=a * 0.9, dx=max(3, int(px * 0.03)), dy=max(4, int(px * 0.035)),
                     blur=max(0.6, px * 0.012))
        X.put(img, sp, L["x"] * C.W, y + adv / 2 + (1 - p) * 18, alpha=a, glow_amt=glow * 1.3)
        y += adv


# ---------------------------------------------------------------- echo
def _echo(img, cue, t):
    text = cue["text"]
    px = cue.get("px") or 150
    color = cue.get("color") or C.CHALK
    t0, t1 = cue["t0"], cue["t1"]
    n = cue.get("copies", 11)
    pout = T.clamp((t - (t1 - 0.2)) / 0.32)
    r = T.rng(int(t0 * 7) + 3)
    drift = (t - t0) * (cue.get("drift_px", 40.0))
    sp = X.text_sprite(text, px, color=color, weight="Black", tracking=0.04,
                       glow=cue.get("glow", 0.3))
    for k in range(n):
        u = k / max(1, n - 1)
        sx = (u - 0.5) * 1.35 * C.W + drift * (0.4 + u * 1.2)
        sy = (0.5 + (u - 0.5) * 0.55) * C.H + np.sin(u * 6 + t * 0.6) * 22
        sc = 0.28 + u * 1.35
        al = (0.06 + 0.30 * (1 - abs(u - 0.5) * 1.6)) * (1 - pout)
        pin = T.clamp((t - t0 - k * 0.03) / 0.25)
        X.put(img, sp, sx, sy, scale=sc, alpha=al * pin)


# ---------------------------------------------------------------- watermark
def _watermark(img, cue, t):
    text = cue["text"]
    px = cue.get("px") or 420
    t0, t1 = cue["t0"], cue["t1"]
    L = layout(cue.get("layout", "bottom_right"))
    sp = X.text_sprite(text, px, color=cue.get("color", (150, 142, 124)), weight="Black",
                       tracking=0.18)
    pin = T.clamp((t - t0) / 0.8)
    pout = T.clamp((t - (t1 - 0.2)) / 0.4)
    X.put(img, sp, L["x"] * C.W, L["y"] * C.H, alpha=cue.get("alpha", 0.11) * pin * (1 - pout))


# ---------------------------------------------------------------- dossier
def _dossier(img, cue, t):
    """A newspaper clipping: vertical headline + 3 columns of small text."""
    L = layout(cue.get("layout", "low_left"))
    t0, t1 = cue["t0"], cue["t1"]
    ttl = cue.get("title") or cue.get("text", "")
    body = cue.get("body") or ("　".join(list(ttl)) * 3)
    pin = T.ease_out(T.clamp((t - t0) / 0.4))
    pout = T.clamp((t - (t1 - 0.2)) / 0.35)
    a = pin * (1 - pout)
    if a <= 0.004:
        return
    tpx = cue.get("px") or 150
    cx = L["x"] * C.W
    cy = L["y"] * C.H + (1 - pin) * 22
    # headline
    sp = X.text_sprite(ttl, int(tpx), color=C.CHALK, weight="Black", tracking=0.06)
    X.put(img, sp, cx, cy, alpha=a)
    # columns of fake body text
    col_w = int(cue.get("col_w", 150))
    line_h = int(cue.get("line_h", 13))
    size = int(cue.get("body_px", 10))
    y = cy + int(tpx) * 0.85
    for ci in range(3):
        x = cx - (3 - 1) * col_w / 2 + ci * col_w
        yy = y
        for li in range(int(cue.get("rows", 16))):
            seg = body[(ci * 37 + li * 5): (ci * 37 + li * 5) + 9]
            if not seg:
                break
            small = X.text_sprite(seg, size, color=(186, 178, 160), weight="Regular",
                                  tracking=0.05)
            X.put(img, small, x, yy, alpha=a * 0.55)
            yy += line_h
    # rule lines
    for ci in range(3):
        x = cx - (3 - 1) * col_w / 2 + ci * col_w - col_w * 0.46
        y0, y1 = int(y - 6), int(y + line_h * cue.get("rows", 16))
        img[max(0, y0):min(C.H, y1), max(0, int(x)):max(0, int(x)) + 1] *= 0.6


# ---------------------------------------------------------------- stamp
def _stamp(img, cue, t, skew_boost=0.0):
    """Text laid onto a plane in perspective."""
    text = cue["text"]
    px = cue.get("px") or 120
    t0, t1 = cue["t0"], cue["t1"]
    L = layout(cue.get("layout", "center"))
    pin = T.ease_out(T.clamp((t - t0) / 0.35))
    pout = T.clamp((t - (t1 - 0.2)) / 0.32)
    a = pin * (1 - pout)
    if a <= 0.004:
        return
    sp = X.text_sprite(text, px, color=cue.get("color") or C.CHALK, weight="Black", tracking=0.05)
    try:
        import cv2
        w, h = sp.img.size
        m = max(8, int(px * 0.30))
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        skew = min(8.0, (cue.get("skew", 6.0) or 6.0) + skew_boost)
        dw = w * (1 + skew / 60.0)      # capped: legibility before effect
        dst = np.float32([[m * 0.6, 0], [w - m * 0.2, m * 0.4],
                          [dw - m * 0.1, h + m * 0.5], [m * 1.2, h - m * 0.1]])
        M = cv2.getPerspectiveTransform(src, dst)
        cw, ch = int(dw) + 4 * m, int(h) + 4 * m
        canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        canvas.paste(sp.img, (2 * m, 2 * m), sp.img)
        warped = cv2.warpPerspective(np.array(canvas), M, (cw, ch),
                                     flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
        arr = np.asarray(warped).astype(np.float32)
        rgb, alp = arr[:, :, :3], arr[:, :, 3] / 255.0 * a
        X._blend(img, rgb, alp, int(L["x"] * C.W - cw / 2), int(L["y"] * C.H - ch / 2))
    except Exception:
        X.put(img, sp, L["x"] * C.W, L["y"] * C.H, alpha=a)


# ---------------------------------------------------------------- extras
def _collide(img, cue, t):
    """Two halves of the line rush in from opposite sides and slam together."""
    text = cue["text"]
    n = len(text)
    cut = max(1, n // 2)
    left, right = text[:cut], text[cut:]
    px = _fit_whole(text, cue.get("px") or fit_px(cut, "center"), frac=0.80)
    px = int(min(px, (C.W - 2 * C.SAFE - 90) / max(1, n)))
    t0, t1 = cue["t0"], cue["t1"]
    p = T.ease_out(T.clamp((t - t0) / 0.42))
    pout = T.clamp((t - (t1 - 0.18)) / 0.3)
    a = (1 - pout)
    gap = (1 - p) * C.W * 0.42
    sl = X.text_sprite(left, px, color=C.CHALK, weight="Black", tracking=0.03, glow=cue.get("glow", 0.5))
    sr = X.text_sprite(right, px, color=C.CHALK, weight="Black", tracking=0.03, glow=cue.get("glow", 0.5))
    cy = C.H * 0.44
    X.put(img, sl, C.W * 0.5 - sl.w / 2 - gap, cy, alpha=a, glow_amt=0.9)
    X.put(img, sr, C.W * 0.5 + sr.w / 2 + gap, cy, alpha=a, glow_amt=0.9)


def _radial(img, cue, t):
    """Glyphs land along radial spokes from the frame centre."""
    text = cue["text"]
    px = cue.get("px") or 130
    t0, t1 = cue["t0"], cue["t1"]
    words = cue.get("words") or []
    pout = T.clamp((t - (t1 - 0.2)) / 0.3)
    chars = X.char_sprites(text, px, color=cue.get("color") or C.CHALK, weight="Black",
                           tracking=0.02, glow=cue.get("glow", 0.5))
    cx0, cy0 = C.W * 0.5, C.H * 0.46
    radius = C.H * 0.30
    for i, (sp, _a) in enumerate(chars):
        ang = -np.pi * 0.75 + i * (1.5 * np.pi / max(1, len(chars) - 1))
        on = float(words[i]["t0"]) if i < len(words) else t0 + i * 0.08
        p = T.ease_out(T.clamp((t - on) / 0.26))
        if p <= 0.004:
            continue
        r = radius * (1.25 - 0.25 * p)
        x = cx0 + np.cos(ang) * r * 1.55
        y = cy0 + np.sin(ang) * r
        X.put_shadow(img, sp, x, y, alpha=p * (1 - pout) * 0.9, dx=5, dy=7, blur=0.7)
        X.put(img, sp, x, y, alpha=p * (1 - pout), glow_amt=0.9)


def _scan(img, cue, t):
    """A scan line sweeps; glyphs brighten as it passes."""
    text = cue["text"]
    px = cue.get("px") or fit_px(len(text), "center")
    t0, t1 = cue["t0"], cue["t1"]
    L = layout(cue.get("layout", "center"))
    words = cue.get("words") or []
    chars = X.char_sprites(text, px, color=cue.get("color") or C.CHALK, weight="Black",
                           tracking=0.02, glow=cue.get("glow", 0.5))
    total = sum(a for _, a in chars)
    x = C.W / 2 - total / 2
    cy = L["y"] * C.H
    pout = T.clamp((t - (t1 - 0.2)) / 0.3)
    sweep = T.clamp((t - t0) / max(0.3, (t1 - t0) * 0.7))
    sx = C.W * (sweep * 1.3 - 0.15)
    for i, (sp, adv) in enumerate(chars):
        on = float(words[i]["t0"]) if i < len(words) else t0
        vis = T.clamp((t - on) / 0.2)
        lit = T.clamp(1.0 - abs((x + adv / 2) - sx) / (C.W * 0.18))
        a = vis * (0.42 + 0.58 * lit) * (1 - pout)
        if a > 0.004:
            X.put(img, sp, x + adv / 2, cy, alpha=a, glow_amt=0.9 + 1.6 * lit)
        x += adv
    # the scan line itself
    xi = int(np.clip(sx, 0, C.W - 3))
    img[:, xi:xi + 3, :] += 55 * (1 - pout)


def _erode(img, cue, t):
    """The right half of each glyph is eaten away."""
    text = cue["text"]
    px = cue.get("px") or fit_px(len(text), "center")
    t0, t1 = cue["t0"], cue["t1"]
    L = layout(cue.get("layout", "center"))
    p = T.ease_out(T.clamp((t - t0) / 0.5))
    pout = T.clamp((t - (t1 - 0.2)) / 0.3)
    sp = X.text_sprite(text, px, color=cue.get("color") or C.CHALK, weight="Black",
                       tracking=0.03, glow=cue.get("glow", 0.5))
    cut = int(sp.w * (1.0 - T.clamp((t - t0 - 0.4) / 0.9) * 0.55))
    rgb = sp.rgb[:, :cut]
    a = sp.a[:, :cut] * p * (1 - pout)
    X._blend(img, rgb, a, int(L["x"] * C.W - sp.w / 2), int(L["y"] * C.H - sp.h / 2))


def _fit_whole(text, px, frac=0.86):
    """Shrink a whole-line sprite so it can never run past the frame."""
    n = max(1, len(text))
    cap = int((C.W - 2 * C.SAFE) * frac / n)
    return max(40, min(int(px), cap))


def _extrude(img, cue, t):
    """Fake 3D: stacked offset copies (side face) + bright front face."""
    text = cue["text"]
    px = _fit_whole(text, cue.get("px") or fit_px(len(text), "center"))
    t0, t1 = cue["t0"], cue["t1"]
    L = layout(cue.get("layout", "center"))
    pin = T.ease_out(T.clamp((t - t0) / 0.4))
    pout = T.clamp((t - (t1 - 0.2)) / 0.3)
    a = pin * (1 - pout)
    face = X.text_sprite(text, px, color=C.CHALK, weight="Black", tracking=0.03, glow=cue.get("glow", 0.5))
    side = X.text_sprite(text, px, color=(46, 36, 28), weight="Black", tracking=0.03)
    depth = int(px * 0.10)
    cx = L["x"] * C.W
    cy = L["y"] * C.H
    for k in range(depth, 0, -2):
        X.put(img, side, cx + k * 0.55, cy + k * 0.75, alpha=a * 0.85)
    X.put(img, face, cx, cy, alpha=a, glow_amt=1.2)



def _frame(img, cue, t):
    """A rectangular wire frame grows first, the text fills it afterwards."""
    t0, t1 = cue["t0"], cue["t1"]
    L = layout(cue.get("layout", "center"))
    w = cue.get("w", 0.42) * C.W
    h = cue.get("h", 0.20) * C.H
    cx, cy = L["x"] * C.W, L["y"] * C.H
    p = T.ease_out(T.clamp((t - t0) / 0.35))
    pout = T.clamp((t - (t1 - 0.2)) / 0.3)
    a = p * (1 - pout)
    if a <= 0.004:
        return
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    x1, y1 = int(cx + w / 2), int(cy + h / 2)
    x1 = int(x0 + w * p)
    th = 2
    for yy in (y0, y0 + 1, y1 - 1, y1):
        img[max(0, yy):max(0, yy) + 1, max(0, x0):min(C.W, x1)] = 220 * a
    for xx in (x0, x0 + 1, x1 - 1, x1):
        img[max(0, y0):min(C.H, y1), max(0, xx):max(0, xx) + 1] = 220 * a
    if p > 0.6:
        sp = X.text_sprite(cue["text"], cue.get("px", 120), color=C.CHALK, weight="Black",
                           tracking=0.05)
        X.put(img, sp, cx, cy, alpha=(p - 0.6) / 0.4 * (1 - pout))


# ---------------------------------------------------------------- dots
def _dots(img, cue, t):
    """Characters reduced to a dot matrix, blinking."""
    text = cue["text"]
    px = cue.get("px") or 160
    t0, t1 = cue["t0"], cue["t1"]
    L = layout(cue.get("layout", "center"))
    pout = T.clamp((t - (t1 - 0.2)) / 0.3)
    sp = X.text_sprite(text, px, color=cue.get("color") or C.CHALK, weight="Black")
    mask = sp.a
    step = 9
    ys, xs = np.nonzero(mask[::step, ::step] > 0.35)
    xs = xs * step
    ys = ys * step
    n = min(len(xs), 2600)
    idx = np.linspace(0, len(xs) - 1, n).astype(int) if len(xs) > n else np.arange(len(xs))
    x0 = L["x"] * C.W - sp.w / 2
    y0 = L["y"] * C.H - sp.h / 2
    p = T.clamp((t - t0) / 0.5)
    for j, k in enumerate(idx):
        px_, py_ = int(x0 + xs[k]), int(y0 + ys[k])
        if not (0 <= px_ < C.W - 3 and 0 <= py_ < C.H - 3):
            continue
        on = T.hash01(j * 0.37, t * 2.2)
        a = T.clamp(p * 1.4) * (0.35 + 0.65 * on) * (1 - pout)
        img[py_:py_ + 3, px_:px_ + 3] += 210 * a





