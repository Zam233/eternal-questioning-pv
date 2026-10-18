# -*- coding: utf-8 -*-
"""Tile frames into contact sheets for review."""
import os
import sys
import glob
from PIL import Image, ImageDraw

def sheet(files, cols, rows, tw, th, out, label_from=None):
    W, H = cols * tw, rows * th
    im = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(im)
    for i, f in enumerate(files[: cols * rows]):
        r, c = divmod(i, cols)
        try:
            t = Image.open(f).convert("RGB").resize((tw - 2, th - 2), Image.LANCZOS)
        except Exception:
            continue
        im.paste(t, (c * tw + 1, r * th + 1))
        d.text((c * tw + 4, r * th + 3), os.path.basename(f)[:12], fill=(255, 210, 120))
    im.save(out, quality=88)
    print(out, im.size)

if __name__ == "__main__":
    src = sys.argv[1]
    cols = int(sys.argv[2]); rows = int(sys.argv[3])
    tw = int(sys.argv[4]); th = int(sys.argv[5])
    out = sys.argv[6]
    files = sorted(glob.glob(os.path.join(src, "*.jpg")) + glob.glob(os.path.join(src, "*.png")))
    per = cols * rows
    n = 0
    for s in range(0, len(files), per):
        chunk = files[s:s + per]
        o = out.replace(".jpg", "_%02d.jpg" % n)
        sheet(chunk, cols, rows, tw, th, o)
        n += 1
