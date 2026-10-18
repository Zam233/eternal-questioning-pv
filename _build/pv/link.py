# -*- coding: utf-8 -*-
"""换场合成器：把换场拆成四个可叠加的"分量"，而不是单选一种。

    dir     方向：left/right/up/down/ul/ur/dl/dr —— 整帧错位（A 出画、B 入画）
    za/zb   推拉：A 用 za 起推、B 用 zb 落定；与 dir 同时存在＝"边推边甩"
    cx/cy   推拉中心：没有 dir 时，B 以 (cx,cy) 为圆心径向揭开（推进/拉远）
    rack    移焦：A 逐渐虚掉、B 从虚焦里捞实（与任何分量并存）
    light   光：black 压黑 / bloom 曝亮，高斯窄脉冲，只有两三帧

任意组合都成立：
    dir            → 纯平移
    dir + za       → 方向＋推
    dir + light    → 方向＋闪光／方向＋黑场
    za/zb (无 dir) → 纯推进 / 纯拉远
    za/zb + light  → 闪光＋推拉、黑场＋推拉
    za/zb + rack   → 推拉＋移焦
    rack alone     → 纯焦点转移
    dir+za+light+rack → 四分量全开
"""
import numpy as np
from PIL import Image, ImageFilter

from . import config as C
from . import scene as S


def _fps():
    return float(C.FPS)


def _render(s, t):
    return S.render_frame(s, t)


def _bez(p, x1=0.42, y1=0.0, x2=0.58, y2=1.0):
    from .camera import _bezier_y
    return _bezier_y(float(np.clip(p, 0.0, 1.0)), x1, y1, x2, y2)


DIRS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1),
        "ul": (-1, -1), "ur": (1, -1), "dl": (-1, 1), "dr": (1, 1)}

_GRID = {}


def grid(W, H):
    g = _GRID.get((W, H))
    if g is None:
        xg = ((np.arange(W, dtype=np.float32) + 0.5) / W - 0.5)[None, :]
        yg = ((np.arange(H, dtype=np.float32) + 0.5) / H - 0.5)[:, None]
        _GRID[(W, H)] = (xg, yg)
    return _GRID[(W, H)]


def gauss(img, sigma):
    if sigma < 0.6:
        return img
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(min(40.0, sigma)))).astype(np.float32)


def shift_clamp(img, dx, dy):
    H, W = img.shape[:2]
    ix, iy = int(round(dx)), int(round(dy))
    if ix == 0 and iy == 0:
        return img
    xs = np.clip(np.arange(W) - ix, 0, W - 1)
    ys = np.clip(np.arange(H) - iy, 0, H - 1)
    return img[ys][:, xs]


def cover(deg, W, H):
    a = abs(np.radians(deg))
    c, s = np.cos(a), np.sin(a)
    return max((W * c + H * s) / W, (W * s + H * c) / H)


def xf(img, scale=1.0, rot=0.0):
    H, W = img.shape[:2]
    scale = max(1.0, scale)
    if abs(scale - 1.0) < 0.002 and abs(rot) < 0.04:
        return img
    s = max(1.0, scale * cover(rot, W, H))
    th = np.radians(rot)
    cs, sn = np.cos(th), np.sin(th)
    cx, cy = W * 0.5, H * 0.5
    a, b = cs / s, sn / s
    d, e = -sn / s, cs / s
    cf = -a * cx - b * cy + cx
    ff = -d * cx - e * cy + cy
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    im = im.transform((W, H), Image.AFFINE, (a, b, cf, d, e, ff), resample=Image.BILINEAR)
    return np.asarray(im).astype(np.float32)


def smear(img, dx, dy, n=9):
    m = max(abs(dx), abs(dy))
    if m < 1.5:
        return img
    if m > 160.0:
        s = 160.0 / m
        dx, dy = dx * s, dy * s
    acc = None
    for i in range(n):
        f = i / (n - 1.0) - 0.5
        s = shift_clamp(img, dx * f, dy * f)
        acc = s if acc is None else acc + s
    return acc / n


def seam(W, H, ux, uy, k, feather=0.030):
    """1 = A, 0 = B；A 沿 (ux,uy) 出画，交界是一条垂直于该方向的直线。"""
    xg, yg = grid(W, H)
    ln = float(np.hypot(ux, uy)) or 1.0
    nx, ny = ux / ln, uy / ln
    lo = -0.5 * (abs(nx) + abs(ny))
    hi = 0.5 * (abs(nx) + abs(ny))
    thr = lo + (hi - lo) * k
    field = xg * nx + yg * ny
    return np.clip((field - thr) / feather + 0.5, 0.0, 1.0).astype(np.float32)[..., None]


def iris(W, H, cx, cy, R, feather=0.07):
    """1 = B（新场景的圆盘），0 = A。"""
    xg, yg = grid(W, H)
    r = np.sqrt((xg - (cx - 0.5)) ** 2 + (yg - (cy - 0.5)) ** 2)
    return np.clip((R - r) / feather + 0.5, 0.0, 1.0).astype(np.float32)[..., None]


def components(L):
    """Read the transition as a set of components (used by the audit too)."""
    return dict(
        dir=L.get("dir"),
        za=float(L.get("za", 1.0)),
        zb=float(L.get("zb", 1.0)),
        cx=float(L.get("cx", 0.5)),
        cy=float(L.get("cy", 0.5)),
        rack=float(L.get("rack", 0.0)),
        light=L.get("light"),
        amt=float(L.get("amt", 0.0)),
        w=float(L.get("w", 0.16)),
        ra=float(L.get("ra", 0.0)),
        rb=float(L.get("rb", 0.0)),
    )


def link_frame(shots, b, t, L):
    W, H = C.W, C.H
    a = shots[int(L["prev"])]
    dur = max(1e-3, float(L["dur"]))
    p = float(np.clip((t - b["t0"]) / dur, 0.0, 1.0))
    q = float(np.clip((t - 1.0 / _fps() - b["t0"]) / dur, 0.0, 1.0))
    k, kp = _bez(p), _bez(q)
    c = components(L)

    A = _render(a, t)
    B = _render(b, t)

    # ---- 移焦分量：两侧各自虚掉，交界也一起软掉
    if c["rack"] > 0.5:
        A = gauss(A, c["rack"] * k)
        B = gauss(B, c["rack"] * (1.0 - k))

    zoomed = (c["za"] > 1.005) or (c["zb"] > 1.005)

    if c["dir"]:
        # ---- 方向分量（可同时推拉）：A 出画、B 入画
        ux, uy = DIRS.get(c["dir"], (-1, 0))
        sy = H if uy and not ux else (W if ux else W)
        dxa, dya = ux * W * k, uy * H * k
        dxb, dyb = -ux * W * (1.0 - k), -uy * H * (1.0 - k)
        ta = (ux * W * kp, uy * H * kp)
        tb = (-ux * W * (1.0 - kp), -uy * H * (1.0 - kp))
        A = smear(A, 0.55 * (dxa - ta[0]), 0.55 * (dya - ta[1]))
        B = smear(B, 0.55 * (dxb - tb[0]), 0.55 * (dyb - tb[1]))
        if zoomed:
            A = xf(shift_clamp(A, dxa, dya), 1.0 + (c["za"] - 1.0) * k, c["ra"] * k)
            B = xf(shift_clamp(B, dxb, dyb), 1.0 + (c["zb"] - 1.0) * (1.0 - k), c["rb"] * (1.0 - k))
        else:
            A = shift_clamp(A, dxa, dya)
            B = shift_clamp(B, dxb, dyb)
        m = seam(W, H, ux, uy, k)
        img = A * m + B * (1.0 - m)
    elif zoomed:
        # ---- 只有推拉：B 以 (cx,cy) 为中心径向揭开
        push = c["za"] > 1.005
        sa = 1.0 + (max(c["za"], 1.0) - 1.0) * k if push else 1.0 + 0.10 * k
        sb = 1.0 + (max(c["zb"], 1.0) - 1.0) * (1.0 - k)
        ox = (c["cx"] - 0.5) * W * 0.10 * (k if push else -k)
        oy = (c["cy"] - 0.5) * H * 0.10 * (k if push else -k)
        A = xf(shift_clamp(A, ox, oy), sa, c["ra"] * k)
        B = xf(B, sb, c["rb"] * (1.0 - k))
        R = (0.02 + 0.80 * k) if push else (0.03 + 0.79 * k)
        m = iris(W, H, c["cx"], c["cy"], R)
        img = A * (1.0 - m) + B * m
    else:
        # ---- 只剩光/焦：满画幅交叠
        img = A * (1.0 - k) + B * k

    # ---- 光分量：高斯窄脉冲，只暗/亮两三帧
    if c["light"] in ("black", "bloom") and c["amt"] > 0.01:
        g = c["amt"] * float(np.exp(-(((k - 0.5) / max(0.05, c["w"])) ** 2)))
        if c["light"] == "black":
            img = img * (1.0 - g)
        else:
            warm = np.array((252, 240, 220), np.float32)[None, None, :]
            img = img * (1.0 - g) + warm * g
    return img
