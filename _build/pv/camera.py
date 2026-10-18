# -*- coding: utf-8 -*-
"""A real pinhole camera driving a stack of 2.5D layers, with rack focus.

        dz = Z - cam.z
        s  = Z / dz                <- scale  (1.0 when the camera is at z=0)
        px = (X - cam.x) * s
        rot= cam.roll              <- the whole frame rolls together
        blur = |Z - focus| * aperture   <- depth of field

Camera keys: (u, x, y, z, roll [, focus])
"""
import numpy as np

from . import config as C
from . import tex as T

GAIN = 1.0



def _bezier_y(t, x1=0.42, y1=0.0, x2=0.58, y2=1.0):
    """Cubic bezier easing (solve x -> y), the curve a real camera move follows."""
    t = float(np.clip(t, 0.0, 1.0))
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = (lo + hi) * 0.5
        bx = 3 * (1 - mid) ** 2 * mid * x1 + 3 * (1 - mid) * mid ** 2 * x2 + mid ** 3
        if bx < t:
            lo = mid
        else:
            hi = mid
    s = (lo + hi) * 0.5
    return 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s ** 2 * y2 + s ** 3

class Cam:
    def __init__(self, spec):
        s = spec or {}
        keys = s.get("keys") or [
            (0.0, 0.0, 0.0, float(s.get("z0", 0.0)), float(s.get("rot0", 0.0)), 0.55),
            (1.0, float(s.get("px", 0.0)), float(s.get("py", 0.0)),
             float(s.get("z1", 0.10)), float(s.get("rot1", 0.0)), 0.55),
        ]
        self.keys = []
        for k in keys:
            k = tuple(k) + (0.55,) * (6 - len(k))
            self.keys.append(k)
        self.keys.sort(key=lambda k: k[0])
        self.handheld = float(s.get("handheld", 1.0))
        self.aperture = float(s.get("aperture", 3.2))
        self.max_blur = float(s.get("max_blur", 6.0))
        self.seed = int(s.get("seed", 3))
        self.nudges = s.get("nudges") or []
        self.dur = float(s.get("dur", 4.0))

    def at(self, u):
        k = self.keys
        if u <= k[0][0]:
            a = b = k[0]; f = 0.0
        elif u >= k[-1][0]:
            a = b = k[-1]; f = 0.0
        else:
            a = b = k[0]; f = 0.0
            for i in range(len(k) - 1):
                if k[i][0] <= u <= k[i + 1][0]:
                    a, b = k[i], k[i + 1]
                    span = max(1e-6, b[0] - a[0])
                    f = _bezier_y((u - a[0]) / span)
                    break
        x = a[1] + (b[1] - a[1]) * f
        y = a[2] + (b[2] - a[2]) * f
        z = a[3] + (b[3] - a[3]) * f
        roll = a[4] + (b[4] - a[4]) * f
        focus = a[5] + (b[5] - a[5]) * f
        for nd in self.nudges:
            c0 = float(nd.get("t", 0.0)) / max(0.1, self.dur)
            w = float(nd.get("w", 0.22))
            g = float(np.exp(-((u - c0) / w) ** 2))
            x += float(nd.get("dx", 0.0)) * g
            y += float(nd.get("dy", 0.0)) * g
            z += float(nd.get("dz", 0.0)) * g
            roll += float(nd.get("dr", 0.0)) * g
        if self.handheld:
            h = 0.0016 * self.handheld
            x += h * np.sin(u * 7.3 + self.seed)
            y += h * np.sin(u * 5.1 + self.seed * 1.7)
            roll += 0.06 * self.handheld * np.sin(u * 3.3 + self.seed * 0.6)
        return x, y, z, roll, focus

    def blur_for(self, st, Z):
        """Depth of field: how far this layer sits from the focal plane."""
        if not self.aperture:
            return 0.0
        return float(np.clip(abs(float(Z) - st[4]) * self.aperture, 0.0, self.max_blur))


def layer_xform(st, Z, size_pow=0.25):
    x, y, z, roll = st[0], st[1], st[2], st[3]
    dz = max(0.08, float(Z) - z)
    k = 1.0 / dz
    s = min(float(Z) * k, 6.0)
    return s, -x * s * GAIN, -y * s * GAIN, roll


