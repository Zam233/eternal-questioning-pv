// Check whether a CUDA-enabled wheel exists for this Python (3.14).
const PY = process.argv[2] || "314";
const idx = [
  "https://pypi.tuna.tsinghua.edu.cn/simple/cupy-cuda12x/",
  "https://pypi.tuna.tsinghua.edu.cn/simple/torch/",
];
for (const url of idx) {
  try {
    const r = await fetch(url, { headers: { "user-agent": "pip/25" } });
    const t = await r.text();
    const m = [...t.matchAll(/[A-Za-z0-9_.+-]+\.whl/g)].map((x) => x[0]);
    const counts = {};
    for (const f of m) {
      const mm = f.match(/cp\d+/);
      const k = mm ? mm[0] : "?";
      counts[k] = (counts[k] || 0) + 1;
    }
    console.log(url.split("/")[4], "wheels", m.length, JSON.stringify(counts));
    const has = m.filter((f) => f.includes("cp" + PY));
    console.log("  cp" + PY + " wheels:", has.length, has.slice(0, 2).join(" "));
  } catch (e) {
    console.log("ERR", url, e.message);
  }
}
