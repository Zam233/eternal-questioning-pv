# -*- coding: utf-8 -*-
"""Transitions applied at the head of a shot, on the composed frame."""
import numpy as np

from . import config as C
from . import tex as T


def flash(arr, p, colour=(252, 248, 240)):
    """White-flash: p in [0,1] = how much white is left."""
    if p <= 0:
        return arr
    w = np.array(colour, np.float32)[None, None, :]
    return arr * (1 - p) + w * p


def streak(arr, amt, seed=0):
    """Horizontal motion smear: average several shifted copies."""
    if amt <= 0.01:
        return arr
    k = max(2, int(2 + 7 * amt))
    out = np.zeros_like(arr)
    rng = T.rng(seed)
    for i in range(k):
        d = int((i - k / 2) * (10 + 120 * amt) * (1 if rng.random() > 0.5 else -1) * 0.35)
        out += np.roll(arr, d, axis=1)
    return out / k


def whip(arr, amt, direction=1):
    """Fast pan smear with a bright leading edge."""
    if amt <= 0.01:
        return arr
    k = 9
    out = np.zeros_like(arr)
    for i in range(k):
        d = int(direction * (i - k // 2) * 40 * amt)
        out += np.roll(arr, d, axis=1)
    out /= k
    if direction > 0:
        out[:, -int(60 * amt):, :] += 26 * amt
    else:
        out[:, :int(60 * amt), :] += 26 * amt
    return out


def tint_jump(arr, amt, colour=(120, 210, 140)):
    if amt <= 0.01:
        return arr
    c = np.array(colour, np.float32)[None, None, :]
    return arr * (1 - 0.45 * amt) + c * (0.45 * amt)


def apply(arr, sh, tl):
    """tl = seconds since this shot started."""
    tr = sh.get("trans_in")
    if not tr:
        return arr
    if tr == "flash":
        return flash(arr, T.clamp(1.0 - tl / 0.13) ** 1.3)
    if tr == "flash_soft":
        return flash(arr, T.clamp(1.0 - tl / 0.26) ** 1.6, (240, 236, 226))
    if tr == "streak":
        return streak(arr, T.clamp(1.0 - tl / 0.20), sh.get("seed", 1))
    if tr == "whip":
        return whip(arr, T.clamp(1.0 - tl / 0.30), sh.get("whip_dir", 1))
    if tr == "tint":
        return tint_jump(arr, T.clamp(1.0 - tl / 0.18), sh.get("tint_rgb", (120, 210, 140)))
    return arr
