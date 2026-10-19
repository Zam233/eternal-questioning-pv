# -*- coding: utf-8 -*-
"""GPU bootstrap + accelerated post-processing chain.

CuPy and the CUDA toolkit may live outside the repo (NVRTC refuses paths that
contain CJK characters), so the three roots below are resolved in this order:

    environment variable  PV_GPU_ROOT / PV_CUDA_ROOT / PV_TMP
    per-machine module    pv/_local_paths.py  (gitignored)
    repo-relative default _gpu / _tmp

Nothing machine-specific is committed.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))

try:                                   # per-machine overrides, never committed
    from . import _local_paths as _lp
except Exception:                      # pragma: no cover
    _lp = None


def _root(env, attr, default):
    return os.environ.get(env) or getattr(_lp, attr, default)


GPU_ROOT = _root("PV_GPU_ROOT", "GPU_ROOT", os.path.join(_REPO, "_gpu"))
CUDA_ROOT = _root("PV_CUDA_ROOT", "CUDA_ROOT", os.path.join(GPU_ROOT, "cuda_root"))
TMP_ROOT = _root("PV_TMP", "TMP_ROOT", os.path.join(_REPO, "_tmp"))

_cp = None
_ready = None


def cp():
    """Return the cupy module, or None when the GPU path is unavailable."""
    global _cp, _ready
    if _ready is not None:
        return _cp
    _ready = False
    try:
        os.makedirs(TMP_ROOT, exist_ok=True)
        os.environ["TMP"] = TMP_ROOT
        os.environ["TEMP"] = TMP_ROOT
        os.environ["CUDA_PATH"] = CUDA_ROOT
        os.environ["CUPY_CACHE_DIR"] = os.path.join(TMP_ROOT, "cupycache")
        binp = os.path.join(CUDA_ROOT, "bin")
        if binp not in os.environ.get("PATH", ""):
            os.environ["PATH"] = binp + ";" + os.environ.get("PATH", "")
        if GPU_ROOT not in sys.path:
            sys.path.insert(0, GPU_ROOT)
        import cupy as _c
        _c.cuda.runtime.getDeviceCount()
        _cp = _c
        _ready = True
    except Exception as e:  # pragma: no cover
        print("[gpu] unavailable:", type(e).__name__, str(e)[:120], flush=True)
        _cp = None
        _ready = False
    return _cp


def info():
    c = cp()
    if c is None:
        return "cpu"
    p = c.cuda.runtime.getDeviceProperties(0)
    name = p["name"].decode() if isinstance(p["name"], bytes) else p["name"]
    return "%s (%s)" % (name, c.__version__)


# ---------------------------------------------------------------- post chain
_uploaded = {}


def _up(name, arr):
    """Cache a float32 array on the device."""
    if name in _uploaded:
        return _uploaded[name]
    c = cp()
    g = c.asarray(arr, dtype=c.float32)
    _uploaded[name] = g
    return g


def post(arr, sh, t, seed, amt, tear, grain_scale, vig, scan, grain_tile):
    """Whole post chain on the GPU. arr is numpy float32 HxWx3."""
    c = cp()
    if c is None:
        return None
    import numpy as np
    g = c.asarray(arr, dtype=c.float32)
    H, W = arr.shape[:2]

    # --- glitch: horizontal slice displacement
    if amt > 0.001:
        r = np.random.default_rng(int(seed) & 0xFFFFFFFF)
        n = int(2 + 10 * amt)
        rows = []
        start = 0
        for _ in range(n):
            y = int(r.integers(0, max(1, H - 2)))
            h = int(r.integers(3, max(4, int(8 + 90 * amt))))
            h = min(h, H - y)
            if h <= 0:
                continue
            dx = int(r.normal(0, 12 + 120 * amt))
            rows.append((y, h, dx, float(r.uniform(0.45, 1.5)) if r.random() < 0.28 * amt else 1.0))
        for y, h, dx, mul in rows:
            seg = g[y:y + h]
            g[y:y + h] = c.roll(seg, dx, axis=1) * mul
        if amt > 0.58:
            s = int(1 + 7 * amt)
            g[:, :, 0] = c.roll(g[:, :, 0], s, axis=1)
            g[:, :, 2] = c.roll(g[:, :, 2], -s, axis=1)
        if tear > 0.01:
            y0 = int(H * (0.15 + 0.7 * r.random()))
            hh = int(H * tear * 0.4)
            g[y0:y0 + hh] = g[y0:y0 + hh][::-1]

    g = g * scan
    g = g + grain_tile * grain_scale
    g = g * vig
    return c.asnumpy(g)
