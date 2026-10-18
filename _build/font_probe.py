# -*- coding: utf-8 -*-
"""Probe fonts: variable-instance support and glyph rendering."""
import os
from PIL import Image, ImageDraw, ImageFont

FONTS = {
    "NotoSerifSC-VF": r"C:\Windows\Fonts\NotoSerifSC-VF.ttf",
    "STZHONGS": r"C:\Windows\Fonts\STZHONGS.TTF",
    "simsunb": r"C:\Windows\Fonts\simsunb.ttf",
    "simhei": r"C:\Windows\Fonts\simhei.ttf",
    "msyhbd": r"C:\Windows\Fonts\msyhbd.ttc",
    "NotoSansSC-VF": r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
    "timesbd": r"C:\Windows\Fonts\timesbd.ttf",
    "georgiab": r"C:\Windows\Fonts\georgiab.ttf",
}

for name, path in FONTS.items():
    if not os.path.exists(path):
        print(name, "MISSING", path)
        continue
    try:
        f = ImageFont.truetype(path, 120)
        info = []
        try:
            names = f.get_variation_names()
            info.append("var_names=" + repr([n.decode("utf-8", "replace") if isinstance(n, bytes) else n for n in names])[:400])
        except Exception as e:
            info.append("no-variations")
        # measure a CJK glyph
        bb = f.getbbox("\u7406")
        info.append("bbox=" + repr(bb))
        print(f"{name:16s} OK  " + " | ".join(info))
    except Exception as e:
        print(f"{name:16s} ERR {e}")
