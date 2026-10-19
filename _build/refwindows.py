import os
import subprocess

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMPROOT = os.environ.get("TMP", os.path.join(ROOT, "_tmp"))
SRC = os.path.join(ROOT, "过期童话.mp4")
TMP = os.path.join(TMPROOT, "refwind")
os.makedirs(TMP, exist_ok=True)
WIN = {"A_0105_0108": (65.0, 68.0), "B_0109_0113": (69.0, 73.0),
       "C_0113_0116": (73.0, 76.0), "D_0133_0136": (93.0, 96.0),
       "E_0214_0222": (134.0, 142.0)}
for name, (a, b) in WIN.items():
    n = 12
    fr = []
    for i in range(n):
        t = a + (b - a) * i / (n - 1)
        p = os.path.join(TMP, "%s_%02d.png" % (name, i))
        if not os.path.exists(p):
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % t, "-i", SRC,
                            "-frames:v", "1", p], check=True)
        im = Image.open(p).convert("RGB").resize((400, 225))
        fr.append(im)
    sheet = Image.new("RGB", (400 * 6, 225 * 2), (0, 0, 0))
    for i, im in enumerate(fr):
        sheet.paste(im, ((i % 6) * 400, (i // 6) * 225))
    sheet.save(os.path.join(TMP, "sheet_%s.png" % name))
    print("ok", name)
