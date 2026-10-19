# -*- coding: utf-8 -*-
"""封面合成：GPT Image 生成的版画底图 + 中文标题排版（16:9 / 4:3）。"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
FONT = r"C:\Windows\Fonts\NotoSerifSC-VF.ttf"
GOLD = (201, 169, 106)
IVORY = (237, 228, 211)


def cover(src, w, h, out, title_px, mark_px, ty, ty_title=0.115, mark_gap=1.52, rule=True):
    im = Image.open(src).convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((max(w, int(im.width * s)), max(h, int(im.height * s))), Image.LANCZOS)
    x0 = (im.width - w) // 2
    y0 = int((im.height - h) * ty)
    im = im.crop((x0, y0, x0 + w, y0 + h))

    a = np.asarray(im, np.float32)
    # 轻微加对比 + 暗角 + 颗粒，跟正片质感对齐
    a = (a - 128.0) * 1.06 + 128.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx / w - 0.5) * 1.15) ** 2 + ((yy / h - 0.5) * 1.0) ** 2)
    vig = np.clip(1.0 - 0.55 * np.clip((r - 0.20) / 0.62, 0, 1) ** 1.6, 0.35, 1.0)
    a = a * vig[..., None]
    rng = np.random.default_rng(11)
    a = a + rng.normal(0, 3.2, (h, w, 1))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(im, "RGBA")

    def font(px):
        f = ImageFont.truetype(FONT, px)
        try:
            f.set_variation_by_name("Black")
        except Exception:
            pass
        return f

    # 标题：逐字绘制，带字距
    f = font(title_px)
    track = int(title_px * 0.10)
    widths = [d.textlength(ch, font=f) for ch in "永恒追问"]
    total = sum(widths) + track * 3
    x = (w - total) / 2
    y = int(h * ty_title)
    # 阴影让字在杂乱底上读得清
    for i, ch in enumerate("永恒追问"):
        d.text((x + 4, y + 5), ch, font=f, fill=(8, 6, 4, 150))
        d.text((x, y), ch, font=f, fill=IVORY + (255,))
        x += widths[i] + track

    # 5A大作：小字、宽字距、金色，标题下方
    fm = font(mark_px)
    mt = int(mark_px * 0.42)
    mw = sum(d.textlength(ch, font=fm) for ch in "5A大作") + mt * 3
    mx = (w - mw) / 2
    my = y + title_px * mark_gap
    for ch in "5A大作":
        d.text((mx, my), ch, font=fm, fill=GOLD + (235,))
        mx += d.textlength(ch, font=fm) + mt

    # 标题下一条极细的金线
    if rule:
        lw = int(w * 0.10)
        ly = int(my + mark_px * 1.9)
        d.rectangle([(w - lw) // 2, ly, (w + lw) // 2, ly + 2], fill=GOLD + (120,))

    im.save(out, quality=95)
    print("wrote", out, im.size)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    cover(os.path.join(HERE, "cover_art_a.png"), 1920, 1080,
          os.path.join(OUT, "永恒追问_封面_16x9.png"), 220, 46, 0.22,
          ty_title=0.100, mark_gap=1.52, rule=True)
    cover(os.path.join(HERE, "cover_art_b.png"), 1440, 1080,
          os.path.join(OUT, "永恒追问_封面_4x3.png"), 150, 38, 0.10,
          ty_title=0.055, mark_gap=1.55, rule=False)
