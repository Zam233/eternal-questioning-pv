// Look for Windows (win_amd64) cp314 wheels for CUDA-enabled packages.
const targets = ["cupy-cuda12x", "torch", "nvidia-cuda-runtime-cu12"];
for (const pkg of targets) {
  const url = `https://pypi.tuna.tsinghua.edu.cn/simple/${pkg}/`;
  try {
    const r = await fetch(url, { headers: { "user-agent": "pip/25" } });
    const t = await r.text();
    const m = [...t.matchAll(/[A-Za-z0-9_.+-]+\.whl/g)].map((x) => x[0]);
    const win = m.filter((f) => f.includes("win_amd64"));
    const win314 = win.filter((f) => f.includes("cp314") || f.includes("py3"));
    console.log(`${pkg}: total ${m.length}, win_amd64 ${win.length}, win+cp314 ${win.filter((f) => f.includes("cp314")).length}`);
    console.log("   sample:", (win.filter((f) => f.includes("cp314"))[0] || win[0] || "none"));
  } catch (e) {
    console.log(pkg, "ERR", e.message);
  }
}
