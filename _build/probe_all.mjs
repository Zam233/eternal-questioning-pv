// Probe every image-capable model, report per-model status; save the first one that works.
import fs from "node:fs";
const BASE = process.env.IMG_BASE || "";
if (!BASE) { console.error("missing IMG_BASE"); process.exit(2); }
const KEY = process.env.IMG_KEY || "";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function j(path, opts = {}, timeout = 180000) {
  const ac = new AbortController();
  const tm = setTimeout(() => ac.abort(), timeout);
  try {
    const r = await fetch(BASE + path, {
      ...opts,
      signal: ac.signal,
      headers: { Authorization: "Bearer " + KEY, "Content-Type": "application/json", ...(opts.headers || {}) },
    });
    const txt = await r.text();
    let body = null;
    try { body = JSON.parse(txt); } catch {}
    return { status: r.status, body, txt };
  } finally {
    clearTimeout(tm);
  }
}

const list = await j("/models");
const ids = (list.body?.data || []).map((m) => m.id);
console.log("models:", ids.join(", "));

const out = [];
for (const id of ids) {
  const t0 = Date.now();
  try {
    const r = await j("/images/generations", {
      method: "POST",
      body: JSON.stringify({ model: id, prompt: "a marble bust of Plato, 19th century steel engraving", n: 1, size: "1024x1024" }),
    });
    const ms = Date.now() - t0;
    const code = r.body?.error?.code || "";
    const d = r.body?.data?.[0];
    const ok = !!(d && (d.b64_json || d.url));
    console.log(`${id.padEnd(24)} HTTP ${r.status} ${String(ms).padStart(6)}ms  ${ok ? "IMAGE OK" : code || (r.txt || "").slice(0, 90)}`);
    if (ok) {
      const buf = d.b64_json ? Buffer.from(d.b64_json, "base64") : Buffer.from(await (await fetch(d.url)).arrayBuffer());
      fs.mkdirSync("_build/assets/probe", { recursive: true });
      fs.writeFileSync(`_build/assets/probe/${id}.png`, buf);
      console.log(`  saved probe/${id}.png ${(buf.length / 1024).toFixed(0)}KB`);
    }
    out.push({ id, status: r.status, ok, code });
  } catch (e) {
    console.log(`${id.padEnd(24)} ERROR ${e.message}`);
    out.push({ id, status: 0, ok: false, code: e.message });
  }
  await sleep(1500);
}
console.log("\nSUMMARY", JSON.stringify(out.filter((o) => o.ok), null, 0) || "none work");
