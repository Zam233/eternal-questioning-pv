# -*- coding: utf-8 -*-
"""Plate motion programs — the camera has a personality, not one constant push."""
import numpy as np

from . import tex as T

# name -> (zoom0, zoom1, pan_x, pan_y, rot_deg, speed_class)
PROGRAMS = {
    "still":   (1.000, 1.020, 0.00, 0.00, 0.0, "0.5-3 px/s"),
    "creep":   (1.010, 1.035, 0.01, 0.00, 0.0, "3-8 px/s"),
    "drift":   (1.030, 1.070, 0.05, -0.02, 0.0, "20-40 px/s"),
    "drift_l": (1.030, 1.070, -0.05, 0.02, 0.0, "20-40 px/s"),
    "push":    (1.000, 1.180, 0.00, 0.00, 0.0, "60-120 px/s"),
    "push_fast": (1.000, 1.260, 0.02, 0.00, 0.0, "120-160 px/s"),
    "pull":    (1.180, 1.000, 0.00, 0.00, 0.0, "60-120 px/s"),
    "rise":    (1.030, 1.140, 0.00, -0.05, 0.0, "40-90 px/s"),
    "fall":    (1.140, 1.020, 0.00, 0.05, 0.0, "40-90 px/s"),
    "orbit":   (1.050, 1.090, 0.03, 0.00, 1.2, "rotating"),
    "hand":    (1.020, 1.090, 0.03, -0.03, 0.4, "8-20 px/s"),
}


def apply(sh, u):
    """Return (zoom, cx, cy, rot) for this shot at normalised time u."""
    name = sh.get("motion", "drift")
    z0, z1, px, py, rd, _ = PROGRAMS.get(name, PROGRAMS["drift"])
    e = T.ease_io(u)
    zoom = z0 + (z1 - z0) * e
    # a slow breathing layer on top so nothing is perfectly linear
    zoom *= 1.0 + 0.006 * np.sin(u * 6.4 + (sh.get("seed", 3) % 7))
    cx = sh.get("cx", 0.5) + px * (e - 0.5) + 0.004 * np.sin(u * 4.1 + 1.7)
    cy = sh.get("cy", 0.5) + py * (e - 0.5) + 0.004 * np.cos(u * 3.6 + 0.4)
    rot = rd * (u - 0.5) * 2.0
    return zoom, cx, cy, rot
