# -*- coding: utf-8 -*-
"""Layered puppet compositor driven by one physical camera (see camera.py).

Draw order is fixed and non-negotiable:
    1. background plates   (far  -> near by Z)
    2. props               (far  -> near by Z)
    3. TYPE — always last, always on top, never covered by a prop
"""
import os
import numpy as np
from PIL import Image, ImageFilter

from . import config as C
from . import tex as T
from . import block as B
from . import camera as CAM

_props = {}


def prop(src, max_side=1400):
    if src in _props:
        return _props[src]
    path = None
    base_dir = os.path.dirname(C.AI)
    for base in (os.path.join(base_dir, "props"), os.path.join(base_dir, "figures"),
                 os.path.join(base_dir, "subjects"), C.AI):
        for ext in (".png", ".webp"):
            p = os.path.join(base, src + ext)
            if os.path.exists(p):
                path = p
                break
        if path:
            break
    if path is None:
        _props[src] = None
        return None
    im = Image.open(path).convert("RGBA")
    s = min(1.0, max_side / max(im.size))
    if s < 1.0:
        im = im.resize((max(2, int(im.width * s)), max(2, int(im.height * s))), Image.LANCZOS)
    _props[src] = im
    return im


def _tone(rgb, palette):
    from .scene import pal
    p = pal(palette)
    lut = T._duotone(p["lo"], p["hi"])
    g = np.clip(rgb.mean(axis=2), 0, 255).astype(np.uint8)
    return lut[g].astype(np.float32)


def _u(spec, t):
    t0, t1 = spec["t0"], spec["t1"]
    return float(np.clip((t - t0) / max(1e-3, t1 - t0), 0, 1))


# ---------------------------------------------------------------- layers
def _blur(arr, r):
    if r <= 0.15:
        return arr
    return np.asarray(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(r))).astype(np.float32)


def grade_frame(img, g):
    """Scene-specific colour grade: key light colour, contrast, lift."""
    if not g:
        return img
    key = np.array(g.get("key", (255, 255, 255)), np.float32)[None, None, :]
    amt = float(g.get("amount", 0.0))
    if amt > 0:
        lum = img.mean(axis=2, keepdims=True)
        tinted = lum * (key / 255.0)
        img = img * (1 - amt) + tinted * amt
    c = float(g.get("contrast", 1.0))
    if abs(c - 1.0) > 0.01:
        img = (img - 128.0) * c + 128.0
    lift = float(g.get("lift", 0.0))
    if lift:
        img = img + lift * 255.0
    return img


def _draw_bg(img, L, cam, st, u):
    s, ox, oy, roll = CAM.layer_xform(st, L.get("z", 1.0))
    from . import scene as S
    im = S.plate_variant(L.get("src", "ruins"), int(L.get("idx", 0)),
                         L.get("mode", "plate"), L.get("palette", "sepia"))
    cx = 0.5 + ox + L.get("pan_x", 0.0) * (u - 0.5)
    cy = 0.5 + oy + L.get("pan_y", 0.0) * (u - 0.5)
    win = S.window(im, cx, cy, s * float(L.get("fit", 1.0)), roll)
    br = max(float(L.get("blur", 0.0)), cam.blur_for(st, L.get("z", 1.0)))
    win = _blur(win, br)
    a = float(L.get("alpha", 1.0))
    if a >= 0.999:
        np.copyto(img, win)
    else:
        np.copyto(img, img * (1 - a) + win * a)
    if L.get("paper", True):
        img += T.paper_tile(int(L.get("idx", 0)) % 5 + 1) * 9.0


def _develop(L, t):
    """Evidence appears by developing out of the dark, and leaves the same way."""
    tin = float(L.get("tin", -1e9))
    tout = float(L.get("tout", 1e9))
    p = np.clip((t - tin) / float(L.get("dur_in", 0.7)), 0, 1)
    q = np.clip((t - tout) / float(L.get("dur_out", 0.6)), 0, 1)
    a = (p * p * (3 - 2 * p)) * (1 - q)
    blur = (1 - p) * float(L.get("dev_blur", 10.0)) + q * float(L.get("dev_blur", 10.0))
    return float(a), float(blur)


def _draw_figure(img, L, cam, st, t):
    """A person plate: develops in, can sit IN FRONT of the type and cover it."""
    im = prop(L.get("src", ""), max_side=1200) or prop(L.get("src", ""))
    if im is None:
        from . import scene as S
        pass
    a_dev, blur = _develop(L, t)
    a_dev *= float(L.get("alpha", 1.0))
    if a_dev <= 0.004:
        return
    Z = L.get("z", 0.40)
    s, ox, oy, roll = CAM.layer_xform(st, Z)
    h = float(L.get("h", 0.75)) * C.H * s
    if L.get("flip"):
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    nw = max(2, int(h * im.width / max(1, im.height)))
    nh = max(2, int(h))
    rs = im.resize((nw, nh), Image.LANCZOS)
    arr = np.asarray(rs).astype(np.float32)
    rgb, a = arr[:, :, :3], arr[:, :, 3] / 255.0
    if not L.get("raw_colour"):
        rgb = _tone(rgb, L.get("palette", "sepia"))
    if blur > 0.3:
        rgb = _blur(rgb, blur)
    # integrate the plate into the scene: feathered torn edge + own shadow
    al = Image.fromarray((a * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(max(1.2, min(nw, nh) * 0.008)))
    a = np.asarray(al).astype(np.float32) / 255.0
    if L.get("tear", True):
        key = ("tear", nw, nh, L.get("seed", 1))
        nz = _props.get(key)
        if nz is None:
            r = np.random.default_rng(int(L.get("seed", 1)) + nw)
            nz = r.random((max(2, nh // 9), max(2, nw // 9))).astype(np.float32)
            nz = np.asarray(Image.fromarray((nz * 255).astype(np.uint8))
                            .resize((nw, nh), Image.BICUBIC)).astype(np.float32) / 255.0
            _props[key] = nz
        a = a * (0.70 + 0.30 * nz)
    px = (L.get("x", 0.5) + ox) * C.W
    py = (L.get("y", 0.55) + oy) * C.H
    from .typefx import _blend
    # cast a shadow into the plate first, in the shot's light direction
    sx = int(px - nw / 2 + nw * 0.05)
    sy = int(py - nh / 2 + nh * 0.035)
    shadow = _blur(a, max(2.0, min(nw, nh) * 0.02))[..., None] * 0.42
    H, W = img.shape[:2]
    x0, y0 = max(0, sx), max(0, sy)
    x1, y1 = min(W, sx + nw), min(H, sy + nh)
    if x1 > x0 and y1 > y0:
        sh = shadow[y0 - sy:y1 - sy, x0 - sx:x1 - sx]
        img[y0:y1, x0:x1] *= (1.0 - sh)
    _blend(img, rgb, a * a_dev, int(px - nw / 2), int(py - nh / 2))


def _draw_map(img, L, cam, st, u):
    """An old chart laid as a plane in perspective, slowly turning."""
    path = os.path.join(os.path.dirname(C.AI), "maps", str(L.get("src", "")) + ".png")
    if not os.path.exists(path):
        return
    key = ("map", L.get("src"), int(L.get("w", 0.62) * 1000))
    im = _props.get(key)
    if im is None:
        im = Image.open(path).convert("RGBA")
        target = int(float(L.get("w", 0.62)) * C.W)
        sc = target / max(1, im.width)
        im = im.resize((target, max(2, int(im.height * sc))), Image.LANCZOS)
        _props[key] = im
    a_dev, _b = _develop(L, L.get("_t", 0.0))
    ang = float(L.get("rot", 0)) + u * float(L.get("rot_speed", 0.0))
    rs = im.rotate(ang, resample=Image.BICUBIC, expand=True)
    arr = np.asarray(rs).astype(np.float32)
    rgb, a = arr[:, :, :3], arr[:, :, 3] / 255.0
    rgb = _tone(rgb, L.get("palette", "sepia"))
    try:
        import cv2
        hgt, wd = rgb.shape[:2]
        m = int(max(4, wd * 0.02))
        srcp = np.float32([[0, 0], [wd, 0], [wd, hgt], [0, hgt]])
        dst = np.float32([[0, m], [wd, 0], [wd, hgt - m * 2], [0, hgt]])
        Mx = cv2.getPerspectiveTransform(srcp, dst)
        rgb = cv2.warpPerspective(rgb, Mx, (wd, hgt), borderValue=(0, 0, 0))
        a = cv2.warpPerspective(a, Mx, (wd, hgt), borderValue=0)
    except Exception:
        pass
    al = float(L.get("alpha", 1.0)) * _dev_alpha(L, u) * a_dev
    from .typefx import _blend
    cx = (L.get("x", 0.5)) * C.W
    cy = (L.get("y", 0.5)) * C.H
    _blend(img, rgb, a * al, int(cx - rgb.shape[1] / 2), int(cy - rgb.shape[0] / 2))


def _dev_alpha(L, u):
    tin = float(L.get("u_in", 0.0))
    p = np.clip((u - tin) / 0.25, 0, 1)
    return float(p * p * (3 - 2 * p))


def _draw_texture(img, L, cam, st, u):
    mode = L.get("mode", "scanline")
    a = float(L.get("alpha", 0.5)) * _dev_alpha(L, u)
    if a <= 0.01:
        return
    if mode == "scanline":
        x = (u * float(L.get("speed", 1.0)) % 1.0) * C.W
        w = float(L.get("width", 0.002)) * C.W
        x0 = int(max(0, x - w))
        x1 = int(min(C.W, x + w))
        if x1 > x0:
            img[:, x0:x1, :] += 90 * a
    elif mode == "writing":
        t = T.paper_tile(int(L.get("seed", 3)), 1.0)
        img *= (1.0 - a * 0.25) + a * 0.25 * (0.6 + 0.8 * (t + 0.5))


def _draw_prop(img, L, cam, st, u):
    im = prop(L.get("src", ""))
    if im is None:
        return
    Z = L.get("z", 0.4)
    s, ox, oy, roll = CAM.layer_xform(st, Z)
    h = float(L.get("h", 0.7)) * C.H * s
    w = h * im.width / max(1, im.height)
    if L.get("flip"):
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    nw, nh = max(2, int(w)), max(2, int(h))
    rs = im.resize((nw, nh), Image.LANCZOS)
    ang = roll + float(L.get("tilt", 0.0))
    if abs(ang) > 0.15:
        rs = rs.rotate(ang, resample=Image.BICUBIC, expand=True)
    arr = np.asarray(rs).astype(np.float32)
    rgb, a = arr[:, :, :3], arr[:, :, 3] / 255.0
    if not L.get("raw_colour"):
        rgb = _tone(rgb, L.get("palette", "sepia"))
    br = max(float(L.get("depth_blur", 0.0)), cam.blur_for(st, Z))
    rgb = _blur(rgb, br)
    px = (L.get("x", 0.5) + ox) * C.W
    py = (L.get("y", 0.62) + oy) * C.H
    from .typefx import _blend
    al = a * float(L.get("alpha", 1.0))
    if L.get("blend") == "multiply":
        # a shadow prop darkens instead of covering
        x0 = int(px - rgb.shape[1] / 2)
        y0 = int(py - rgb.shape[0] / 2)
        H, W = img.shape[:2]
        sx0, sy0 = max(0, -x0), max(0, -y0)
        dx0, dy0 = max(0, x0), max(0, y0)
        dx1, dy1 = min(W, x0 + rgb.shape[1]), min(H, y0 + rgb.shape[0])
        if dx1 > dx0 and dy1 > dy0:
            sub = img[dy0:dy1, dx0:dx1]
            al_w = al[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)][:, :, None]
            shade = 0.35 + 0.65 * (rgb[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)] / 255.0)
            sub *= (1 - al_w) + al_w * shade
    else:
        _blend(img, rgb, al, int(px - arr.shape[1] / 2), int(py - arr.shape[0] / 2))


def _draw_type(img, L, cam, st, t):
    cue = dict(L.get("cue") or {})
    if not cue.get("text"):
        return
    # the shot owns the cue: never let a line outlive the shot that carries it
    st1 = L.get("_shot_t1")
    if st1 is not None:
        cue["t1"] = min(float(cue.get("t1", st1)), float(st1) - 0.02)
    s, ox, oy, roll = CAM.layer_xform(st, L.get("z", 0.34))
    base = cue.get("px") or 200
    n = max(1, len(cue.get("text", "")))
    want = base * s
    limit = (C.W - 2 * C.SAFE - 60) / n
    cue["px"] = int(min(want, limit))
    cue["_cam_dx"] = ox
    cue["_cam_dy"] = oy
    if abs(roll) > 0.2:
        cue["rot"] = float(cue.get("rot", 0.0)) + roll
    B.draw(img, cue, t)


# ---------------------------------------------------------------- compose
def compose(spec, t):
    img = np.zeros((C.H, C.W, 3), np.float32)
    cam = CAM.Cam(spec.get("cam"))
    st = cam.at(_u(spec, t))
    layers = spec.get("layers", [])
    pal_name = spec.get("palette", "sepia")
    for L in layers:
        L.setdefault("palette", pal_name)

    visual = [L for L in layers if L.get("t", "bg") in ("bg", "prop", "fx", "figure", "map", "texture")
              and not L.get("front")]
    visual.sort(key=lambda L: -float(L.get("z", 1.0)))
    for L in visual:
        k = L.get("t", "bg")
        if k == "bg":
            _draw_bg(img, L, cam, st, _u(spec, t))
        elif k == "fx":
            from . import particles as FX
            FX.draw(img, L, cam, st, _u(spec, t))
        elif k == "figure":
            _draw_figure(img, L, cam, st, t)
        elif k == "map":
            L["_t"] = t
            _draw_map(img, L, cam, st, _u(spec, t))
        elif k == "texture":
            _draw_texture(img, L, cam, st, _u(spec, t))
        else:
            _draw_prop(img, L, cam, st, _u(spec, t))

    img = grade_frame(img, spec.get("grade"))

    # type always on top — a prop must never eat a sung syllable
    for L in layers:
        if L.get("t") == "type":
            L["_shot_t1"] = spec["t1"]
            _draw_type(img, L, cam, st, t)

    # front layers: a narrow subject may sit over the type and take a character
    front = [L for L in layers if L.get("front")]
    front.sort(key=lambda L: -float(L.get("z", 0.3)))
    for L in front:
        k = L.get("t", "prop")
        if k == "figure":
            _draw_figure(img, L, cam, st, t)
        elif k == "prop":
            _draw_prop(img, L, cam, st, _u(spec, t))
        elif k == "texture":
            _draw_texture(img, L, cam, st, _u(spec, t))
    return img

