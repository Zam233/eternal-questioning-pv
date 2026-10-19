import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMPROOT = os.environ.get("TMP", os.path.join(ROOT, "_tmp"))
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)
cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
       "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "320x180", "-r", "24",
       "-i", "-", "-t", "0.2",
       "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
       os.path.join(OUT, "pipe_test.mp4")]
print("trying Popen with stdin=PIPE ...")
try:
    log = open(os.path.join(OUT, "pipe_test.log"), "wb")
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
    frame = bytes(320 * 180 * 3)
    for _ in range(5):
        p.stdin.write(frame)
    p.stdin.close()
    p.wait()
    log.close()
    print("OK rc=", p.returncode, "size", os.path.getsize(os.path.join(OUT, "pipe_test.mp4")))
except Exception as e:
    print("FAIL", type(e).__name__, e)
