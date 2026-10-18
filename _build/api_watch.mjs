// Watch the relay until it recovers, then save a probe image and drop a marker file.
import fs from "node:fs";
const BASE = "https://api.tk1688.com/v1";
const KEY = process.env.IMG_KEY || "";
const MARK = "_build/API_RECOVERED.txt";
const LOG = "_build/api_watch.log";

const stamp = () => new Date().toISOString().replace("T", " ").slice(0, 19);
const log = (s) => { console.log(s); try { fs.appendFileSync(LOG, s + "\n"); } catch {} };

async function tryOnce() {
  const r = await fetch(BASE + "/images/generations", {
    method: "POST",
    headers: { Authorization: "Bearer " + KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ model: "gpt-image-2.5", prompt: "a marble bust, engraving", n: 1, size: "1024x1024" }),
  });
  const txt = await r.text();
  let body = null; try { body = JSON.parse(txt); } catch {}
  const d = body?.data?.[0];
  if (d && (d.b64_json || d.url)) {
    const buf = d.b64_json ? Buffer.from(d.b64_json, "base64") : Buffer.from(await (await fetch(d.url)).arrayBuffer());
    fs.mkdirSync("_build/assets/probe", { recursive: true });
    fs.writeFileSync("_build/assets/probe/recovered.png", buf);
    fs.writeFileSync(MARK, stamp() + "\nprobe bytes=" + buf.length + "\n");
    return { ok: true, note: "image saved" };
  }
  return { ok: false, note: body?.error?.code || ("HTTP " + r.status) };
}

for (let i = 0; i < 40; i++) {
  try {
    const res = await tryOnce();
    if (res.ok) { log(`${stamp()}  RECOVERED  ${res.note}`); process.exit(0); }
    log(`${stamp()}  still down: ${res.note}`);
  } catch (e) {
    log(`${stamp()}  error: ${e.message}`);
  }
  await new Promise((r) => setTimeout(r, 180000));
}
log(`${stamp()}  gave up after 40 tries (2h)`);
