# -*- coding: utf-8 -*-
"""Global configuration for the PV renderer."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.dirname(BUILD)

# 所有临时/缓存目录一律落在 K 盘，不写 C 盘
TMP = os.path.join(ROOT, "_tmp")
os.makedirs(TMP, exist_ok=True)
for _k in ("TEMP", "TMP", "TMPDIR"):
    os.environ[_k] = TMP

W, H = 1920, 1080
FPS = 24
DUR = 262.80
NFRAMES = int(round(DUR * FPS))

AUDIO = os.path.join(ROOT, "\u8ffd\u95ee\u4e00\u4e0b.mp3")
ASSETS = os.path.join(ROOT, "assets")
AI = os.path.join(BUILD, "assets", "ai")          # GPT-Image 2.5 主视觉（24 张）
MET = os.path.join(ASSETS, "met_full")            # 公版版画（第二层）
CACHE = os.path.join(BUILD, "cache")
OUT = os.path.join(ROOT, "out")

FONT_DIR = r"C:\Windows\Fonts"
F_SERIF = os.path.join(FONT_DIR, "NotoSerifSC-VF.ttf")     # Black instance = heavy Ming/Song
F_SANS = os.path.join(FONT_DIR, "NotoSansSC-VF.ttf")
F_LATIN = os.path.join(FONT_DIR, "georgiab.ttf")
F_LATIN_S = os.path.join(FONT_DIR, "times.ttf")
F_HEI = os.path.join(FONT_DIR, "simhei.ttf")

INK = (13, 11, 9)
PAPER = (216, 205, 183)
CHALK = (242, 236, 222)
GOLD = (222, 197, 140)
OCHRE = (198, 152, 92)

SAFE = 96
