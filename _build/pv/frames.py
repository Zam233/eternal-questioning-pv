# -*- coding: utf-8 -*-
"""Frame compositor.

Two ways a scene hands over to the next:
  * DISSOLVE  – shots overlap in time and cross-fade (used inside a passage)
  * THROUGH   – no overlap at all: the outgoing shot zoom / rise / trucks *through*
                the frame in its last ~0.4 s, and the incoming one starts already
                displaced and settles. Matched at the cut, so it reads as one
                continuous camera move rather than a cut.
"""
import numpy as np
from PIL import Image, ImageFilter

from . import config as C
from . import scene as S


def active(shots, t):
    return [s for s in shots if s["t0"] - 1e-6 <= t <= s["t1"] + 1e-6]


# ---------------------------------------------------------------- camera moves
def _zoom_scale(img, s, cx=0.5, cy=0.5):
    if abs(s - 1.0) < 0.004:
        return img
    H, W = img.shape[:2]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    nw, nh = max(2, int(W / s)), max(2, int(H / s))
    x0 = int(cx * W - nw / 2)
    y0 = int(cy * H - nh / 2)
    x0 = max(0, min(W - nw, x0))
    y0 = max(0, min(H - nh, y0))
    im = im.crop((x0, y0, x0 + nw, y0 + nh)).resize((W, H), Image.BILINEAR)
    return np.asarray(im).astype(np.float32)


def _pan_zoom(img, dx, dy):
    """Pan the camera by (dx, dy) screen pixels, zooming just enough to stay filled."""
    H, W = img.shape[:2]
    if abs(dx) < 1 and abs(dy) < 1:
        return img
    s = 1.0 + 2.0 * max(abs(dx) / float(W), abs(dy) / float(H))
    nw, nh = max(2, int(W / s)), max(2, int(H / s))
    cx = W * 0.5 - dx / s
    cy = H * 0.5 - dy / s
    x0 = int(np.clip(cx - nw / 2, 0, W - nw))
    y0 = int(np.clip(cy - nh / 2, 0, H - nh))
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    im = im.crop((x0, y0, x0 + nw, y0 + nh)).resize((W, H), Image.BILINEAR)
    return np.asarray(im).astype(np.float32)


def _zoom_blur(img, amt, n=5, cx=0.5, cy=0.5):
    if amt <= 0.01:
        return img
    acc = np.zeros_like(img)
    for i in range(n):
        acc += _zoom_scale(img, 1.0 + amt * (i / max(1, n - 1)), cx, cy)
    return acc / n


def _shift(img, dx, dy):
    H, W = img.shape[:2]
    dx = int(np.clip(dx, -W + 1, W - 1))
    dy = int(np.clip(dy, -H + 1, H - 1))
    if dx == 0 and dy == 0:
        return img
    out = np.empty_like(img)
    if dx > 0:
        out[:, dx:] = img[:, :W - dx]
        out[:, :dx] = img[:, :dx][:, ::-1]
    elif dx < 0:
        out[:, :W + dx] = img[:, -dx:]
        out[:, W + dx:] = img[:, W + dx:][:, ::-1]
    else:
        out[:] = img
    if dy > 0:
        out[dy:, :] = out[:H - dy, :]
        out[:dy, :] = out[:dy, :][::-1, :]
    elif dy < 0:
        out[:H + dy, :] = out[-dy:, :]
        out[H + dy:, :] = out[H + dy:, :][::-1, :]
    return out


def _ease(p):
    p = float(np.clip(p, 0, 1))
    return p * p * (3 - 2 * p)


def _bez(p, x1=0.36, y1=0.0, x2=0.64, y2=1.0):
    p = float(np.clip(p, 0, 1))
    from .camera import _bezier_y
    return _bezier_y(p, x1, y1, x2, y2)


def _pan_fill(img, dx, dy=0):
    """Translate the frame; the exposed strip is filled with a blurred stretch of
    the adjacent edge, so it reads as motion smear instead of a mirror or a bar."""
    H, W = img.shape[:2]
    dx = int(np.clip(dx, -W + 8, W - 8))
    dy = int(np.clip(dy, -H + 8, H - 8))
    out = np.empty_like(img)
    if dx > 0:
        out[:, dx:] = img[:, :W - dx]
        band = img[:, :max(2, min(14, W - dx))]
        band = np.asarray(Image.fromarray(np.clip(band, 0, 255).astype(np.uint8))
                          .resize((dx, H), Image.BILINEAR)).astype(np.float32)
        band = np.asarray(Image.fromarray(np.clip(band, 0, 255).astype(np.uint8))
                          .filter(ImageFilter.GaussianBlur(max(2, dx * 0.05)))).astype(np.float32)
        out[:, :dx] = band
    elif dx < 0:
        out[:, :W + dx] = img[:, -dx:]
        band = img[:, W + dx:]
        band = np.asarray(Image.fromarray(np.clip(band, 0, 255).astype(np.uint8))
                          .resize((-dx, H), Image.BILINEAR)).astype(np.float32)
        band = np.asarray(Image.fromarray(np.clip(band, 0, 255).astype(np.uint8))
                          .filter(ImageFilter.GaussianBlur(max(2, -dx * 0.05)))).astype(np.float32)
        out[:, W + dx:] = band
    else:
        out[:] = img
    if dy:
        tmp = out
        out = np.empty_like(tmp)
        if dy > 0:
            out[dy:, :] = tmp[:H - dy, :]
            band = tmp[:max(2, min(14, H - dy))]
            band = np.asarray(Image.fromarray(np.clip(band, 0, 255).astype(np.uint8))
                              .resize((W, dy), Image.BILINEAR)).astype(np.float32)
            out[:dy, :] = np.asarray(Image.fromarray(np.clip(band, 0, 255).astype(np.uint8))
                                     .filter(ImageFilter.GaussianBlur(max(2, dy * 0.05)))).astype(np.float32)
        else:
            out[:H + dy, :] = tmp[-dy:, :]
            band = tmp[H + dy:]
            band = np.asarray(Image.fromarray(np.clip(band, 0, 255).astype(np.uint8))
                              .resize((W, -dy), Image.BILINEAR)).astype(np.float32)
            out[H + dy:, :] = np.asarray(Image.fromarray(np.clip(band, 0, 255).astype(np.uint8))
                                         .filter(ImageFilter.GaussianBlur(max(2, -dy * 0.05)))).astype(np.float32)
    return out


def _flare(img, k, side="left"):
    """A warm light seam where the incoming scene slides in."""
    if k <= 0.01:
        return img
    H, W = img.shape[:2]
    band = int(W * 0.18)
    if side == "left":
        x0, x1 = 0, band
    else:
        x0, x1 = W - band, W
    ramp = np.linspace(1.0, 0.0, band, dtype=np.float32)[None, :, None]
    if side == "right":
        ramp = ramp[:, ::-1]
    img[:, x0:x1] += ramp * (150.0 * k)
    return img


def _boundary(img, shot, t, is_in):
    tr = shot.get("tr_in") if is_in else shot.get("tr_out")
    if not tr:
        return img
    ramp = max(0.05, float(tr.get("ramp", 0.42)))
    if is_in:
        k = 1.0 - _bez((t - shot["t0"]) / ramp)
    else:
        k = 1.0 - _bez((shot["t1"] - t) / ramp)
    if k <= 0.004:
        return img
    kind = tr.get("kind", "zoom")
    amt = float(tr.get("amt", 3.0))
    px = float(tr.get("px", 900))
    py = float(tr.get("py", 0))
    if kind == "zoom":
        img = _zoom_blur(img, 0.8 * k)
        return _zoom_scale(img, 1.0 + (amt - 1.0) * k)
    if kind == "zoom_out":
        s = 1.0 + (amt - 1.0) * k
        return _zoom_blur(_zoom_scale(img, s), 0.55 * k)
    if kind == "truck":
        out = _pan_fill(img, int(k * px))
        return _flare(out, k, "left" if px > 0 else "right")
    if kind == "rise":
        out = _pan_fill(img, 0, int(k * py or px))
        return _flare(out, k * 0.7, "left")
    if kind == "diag":
        out = _pan_fill(img, int(k * px), int(k * py))
        return _flare(out, k * 0.8, "left" if px > 0 else "right")
    if kind == "push_truck":
        # 一边推镜一边横向甩出：下一个场景从另一侧进入
        out = _pan_fill(img, int(k * px))
        out = _zoom_blur(out, 0.6 * k)
        return _flare(_zoom_scale(out, 1.0 + (amt - 1.0) * k), k, "left" if px > 0 else "right")
    if kind == "spin":
        out = _zoom_scale(img, 1.0 + (amt - 1.0) * k)
        out = _rotate(out, k * float(tr.get("deg", 10.0)))
        return _flare(out, k * 0.5, "left")
    if kind == "drop":
        out = _pan_fill(img, int(k * px * 0.35), -int(k * (py or px)))
        return _flare(out, k * 0.7, "left")
    if kind == "roll":
        out = _zoom_scale(img, 1.0 + (amt - 1.0) * k)
        return _rotate(out, k * float(tr.get("deg", 7.0)))
    return img

def _rotate(img, deg):
    if abs(deg) < 0.05:
        return img
    H, W = img.shape[:2]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    im = im.rotate(deg, resample=Image.BICUBIC)
    return np.asarray(im).astype(np.float32)


# ---------------------------------------------------------------- linked slide
# A "link" walks shot A out of frame while shot B enters from the opposite side.
# Both shots are rendered for the whole overlap, so the area A vacates is already
# covered by B — no edge stretch, no empty strip, no flash: it reads as one whip.
_DIRS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1),
         "ul": (-1, -1), "ur": (1, -1), "dl": (-1, 1), "dr": (1, 1)}
_GRID = {}


def _grid(W, H):
    g = _GRID.get((W, H))
    if g is None:
        xg = ((np.arange(W, dtype=np.float32) + 0.5) / W - 0.5)[None, :]
        yg = ((np.arange(H, dtype=np.float32) + 0.5) / H - 0.5)[:, None]
        g = (xg, yg)
        _GRID[(W, H)] = g
    return g


def _cover(deg, W, H):
    """Smallest zoom that keeps a rotated frame free of empty corners."""
    a = abs(np.radians(deg))
    c, s = np.cos(a), np.sin(a)
    return max((W * c + H * s) / W, (W * s + H * c) / H)


def _shift_clamp(img, dx, dy):
    """Translate with edge-clamped sampling (no mirror, no black)."""
    H, W = img.shape[:2]
    ix, iy = int(round(dx)), int(round(dy))
    if ix == 0 and iy == 0:
        return img
    xs = np.clip(np.arange(W) - ix, 0, W - 1)
    ys = np.clip(np.arange(H) - iy, 0, H - 1)
    return img[ys][:, xs]


def _xf(img, scale=1.0, rot=0.0):
    """Zoom + roll about the frame centre (scale floored at 1 so no edge floods)."""
    H, W = img.shape[:2]
    scale = max(1.0, scale)
    if abs(scale - 1.0) < 0.002 and abs(rot) < 0.04:
        return img
    s = max(1.0, scale * _cover(rot, W, H))
    th = np.radians(rot)
    cs, sn = np.cos(th), np.sin(th)
    cx, cy = W * 0.5, H * 0.5
    a, b = cs / s, sn / s
    d, e = -sn / s, cs / s
    cf = -a * cx - b * cy + cx
    ff = -d * cx - e * cy + cy
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    im = im.transform((W, H), Image.AFFINE, (a, b, cf, d, e, ff),
                      resample=Image.BILINEAR)
    return np.asarray(im).astype(np.float32)


def _smear(img, dx, dy, n=9):
    m = max(abs(dx), abs(dy))
    if m < 1.5:
        return img
    if m > 160.0:                      # keep the smear a smear, not a flattening
        s = 160.0 / m
        dx, dy = dx * s, dy * s
    acc = None
    for i in range(n):
        f = i / (n - 1.0) - 0.5
        s = _shift_clamp(img, dx * f, dy * f)
        acc = s if acc is None else acc + s
    return acc / n


def _seam(W, H, ux, uy, k, feather=0.030):
    """1 = shot A, 0 = shot B."""
    xg, yg = _grid(W, H)
    nx, ny = ux, uy
    ln = float(np.hypot(nx, ny)) or 1.0
    nx, ny = nx / ln, ny / ln
    lo = -0.5 * (abs(nx) + abs(ny))
    hi = 0.5 * (abs(nx) + abs(ny))
    thr = lo + (hi - lo) * k
    field = xg * nx + yg * ny
    m = (field - thr) / feather + 0.5
    return np.clip(m, 0.0, 1.0).astype(np.float32)[..., None]


def _parts(L, k, W, H):
    ux, uy = _DIRS.get(L.get("out", "left"), (-1, 0))
    dxa, dya = ux * W * k, uy * H * k
    dxb, dyb = -ux * W * (1.0 - k), -uy * H * (1.0 - k)
    za = 1.0 + (float(L.get("za", 1.0)) - 1.0) * k
    zb = 1.0 + (float(L.get("zb", 1.0)) - 1.0) * (1.0 - k)
    ra = float(L.get("ra", 0.0)) * k
    rb = float(L.get("rb", 0.0)) * (1.0 - k)
    return (dxa, dya, za, ra), (dxb, dyb, zb, rb)


def _gauss(img, sigma):
    if sigma < 0.6:
        return img
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(min(40.0, sigma)))).astype(np.float32)


def _iris(W, H, cx, cy, R, feather=0.07):
    """1 = incoming shot B, 0 = outgoing A. A disc that grows out of (cx, cy)."""
    xg, yg = _grid(W, H)
    r = np.sqrt((xg - (cx - 0.5)) ** 2 + (yg - (cy - 0.5)) ** 2)
    return np.clip((R - r) / feather + 0.5, 0.0, 1.0).astype(np.float32)[..., None]


def _link_frame(shots, b, t, L):
    """实现在 pv/link.py：换场是"方向 / 推拉 / 移焦 / 光"四分量的任意叠加。"""
    from . import link as K
    return K.link_frame(shots, b, t, L)


def _link_frame_legacy(shots, b, t, L):
    W, H = C.W, C.H
    a = shots[int(L["prev"])]
    dur = max(1e-3, float(L["dur"]))
    p = float(np.clip((t - b["t0"]) / dur, 0.0, 1.0))
    q = float(np.clip((t - 1.0 / C.FPS - b["t0"]) / dur, 0.0, 1.0))
    k = _bez(p, 0.42, 0.0, 0.58, 1.0)
    kp = _bez(q, 0.42, 0.0, 0.58, 1.0)
    mode = L.get("mode", "slide")
    A = _render(a, t)
    B = _render(b, t)

    # ---- 虚焦 / 黑场 / 闪光：满画幅交叠，靠"光"完成换场，画面不位移
    if mode in ("rack", "blackout", "bloom"):
        ab = float(L.get("blur", 16.0))
        A = _gauss(A, ab * k)
        B = _gauss(B, ab * (1.0 - k))
        w = k
        out = A * (1.0 - w) + B * w
        if mode == "blackout":
            # 镜头推/拉穿进一段没有光的空间：只暗两三帧，再从黑里显出新场景
            g = float(L.get("dip", 0.92)) * np.exp(-(((k - 0.5) / float(L.get("w", 0.18))) ** 2))
            out = out * (1.0 - g)
        elif mode == "bloom":
            # 推进一盏光里：暖白只炸两三帧，不换色相、不瞬切
            g = float(L.get("peak", 0.78)) * np.exp(-(((k - 0.5) / float(L.get("w", 0.15))) ** 2))
            warm = np.array((252, 240, 220), np.float32)[None, None, :]
            out = out * (1.0 - g) + warm * g
        return out

    # ---- 推进 / 拉远：从中点钻进去（或让新空间从小长出来），径向揭开
    if mode in ("push", "pull"):
        cx, cy = float(L.get("cx", 0.5)), float(L.get("cy", 0.5))
        if mode == "push":
            sa_s = 1.0 + (float(L.get("za", 1.95)) - 1.0) * k
            sb_s = 1.0 + (float(L.get("zb", 1.55)) - 1.0) * (1.0 - k)
        else:
            sa_s = 1.0 + 0.10 * k
            sb_s = 1.0 + (float(L.get("zb", 2.20)) - 1.0) * (1.0 - k)
        # 一点点朝中心的位移，才像"往前走"，不像"放大"
        ox = (cx - 0.5) * W * 0.10 * (k if mode == "push" else -k)
        oy = (cy - 0.5) * H * 0.10 * (k if mode == "push" else -k)
        A = _xf(_shift_clamp(A, ox, oy), sa_s, float(L.get("ra", 0.0)) * k)
        B = _xf(B, sb_s, float(L.get("rb", 0.0)) * (1.0 - k))
        R = (0.02 + 0.80 * k) if mode == "push" else (0.03 + 0.79 * k)
        m = _iris(W, H, cx, cy, R)
        return A * (1.0 - m) + B * m

    # ---- 平移（也可是"边推边横甩"）
    sa, sb = _parts(L, k, W, H)
    ta, tb = _parts(L, kp, W, H)
    A = _smear(A, 0.55 * (sa[0] - ta[0]), 0.55 * (sa[1] - ta[1]))
    B = _smear(B, 0.55 * (sb[0] - tb[0]), 0.55 * (sb[1] - tb[1]))
    A = _xf(_shift_clamp(A, sa[0], sa[1]), sa[2], sa[3])
    B = _xf(_shift_clamp(B, sb[0], sb[1]), sb[2], sb[3])
    ux, uy = _DIRS.get(L.get("out", "left"), (-1, 0))
    m = _seam(W, H, ux, uy, k)
    return A * m + B * (1.0 - m)


# ---------------------------------------------------------------- compose
def _render(s, t):
    img = S.render_frame(s, t)
    img = _boundary(img, s, t, True)
    img = _boundary(img, s, t, False)
    return img


def _draw_anchor(img, shots, t):
    a = None
    for s in shots:
        if s.get("anchor"):
            a = s["anchor"]
            break
    if not a:
        return img
    from . import block as B
    cue = dict(kind=a.get("kind", "note"), text=a["text"], t0=-1e9, t1=1e9,
               layout=a.get("layout", "bottom_left"), px=a.get("px", 26),
               alpha=a.get("alpha", 0.55), words=[], glow=0.0, auto_color=False,
               raw_text=True, color=a.get("color", (206, 198, 180)), seed=1)
    B.draw(img, cue, t)
    return img


def frame_at(shots, t):
    for b in shots:
        L = b.get("link")
        if not L:
            continue
        if b["t0"] - 1e-6 <= t <= b["t0"] + float(L["dur"]) + 1e-6:
            return _draw_anchor(_link_frame(shots, b, t, L), shots, t)
    act = active(shots, t)
    if not act:
        prev = [s for s in shots if s["t1"] < t]
        if not prev:
            return np.zeros((C.H, C.W, 3), np.float32)
        sh = max(prev, key=lambda s: s["t1"])
        return _draw_anchor(_render(sh, sh["t1"] - 1e-3), shots, t)
    if len(act) == 1:
        return _draw_anchor(_render(act[0], t), shots, t)

    acc = None
    wsum = 0.0
    for s in act:
        xf = float(s.get("xfade", 0.6))
        if xf <= 1e-4:
            w = 1.0 if s["t0"] <= t <= s["t1"] else 0.0
        else:
            pin = 1.0 if t >= s["t0"] + xf else (t - s["t0"]) / xf
            pout = 1.0 if t <= s["t1"] - xf else max(0.0, (s["t1"] - t) / xf)
            w = max(0.0, min(pin, pout))
            w = w * w * (3 - 2 * w)
        if w <= 0.001:
            continue
        img = _render(s, t)
        acc = img * w if acc is None else acc + img * w
        wsum += w
    if acc is None or wsum <= 1e-6:
        return _draw_anchor(_render(act[0], t), shots, t)
    return _draw_anchor(acc / wsum, shots, t)








