// Batch image generation against the OpenAI-compatible endpoint.
// usage: node gen.mjs <spec.json> [--only=name] [--concurrency=3] [--model=gpt-image-2.5]
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.IMG_BASE || "https://ai.tk1688.com/v1";
const KEY = process.env.IMG_KEY || "";
if (!KEY) { console.error("missing IMG_KEY"); process.exit(2); }

const args = process.argv.slice(2);
const specPath = args.find((a) => !a.startsWith("--"));
const flag = (n, d) => {
  const a = args.find((x) => x.startsWith(`--${n}=`));
  return a ? a.split("=").slice(1).join("=") : d;
};
const only = flag("only", null);
const model = flag("model", "gpt-image-2.5");
const size = flag("size", "1536x1024");
const conc = parseInt(flag("concurrency", "3"), 10);

const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
const outDir = path.resolve(path.dirname(specPath), spec.outDir || "assets/raw");
fs.mkdirSync(outDir, { recursive: true });

const style = spec.style || "";
let items = spec.items;
if (only) items = items.filter((i) => i.name === only);

const manifestPath = path.join(outDir, "manifest.json");
let manifest = {};
try { manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8")); } catch {}

async function genOne(item) {
  const dest = path.join(outDir, item.name + ".png");
  if (fs.existsSync(dest) && fs.statSync(dest).size > 20000 && !flag("force", "")) {
    console.log(`[skip] ${item.name} exists`);
    return;
  }
  const prompt = style + "\n\n" + item.prompt;
  const t0 = Date.now();
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const reqBody = { model, prompt, n: 1, size, quality: "high", response_format: "b64_json" };
      if (spec.transparent) reqBody.background = "transparent";
      const r = await fetch(BASE + "/images/generations", {
        method: "POST",
        headers: { Authorization: "Bearer " + KEY, "Content-Type": "application/json" },
        body: JSON.stringify(reqBody),
      });
      const txt = await r.text();
      let body;
      try { body = JSON.parse(txt); } catch { body = null; }
      if (!r.ok || !body) { throw new Error(`HTTP ${r.status}: ${txt.slice(0, 300)}`); }
      const d = body.data?.[0];
      let buf = null;
      if (d?.b64_json) buf = Buffer.from(d.b64_json, "base64");
      else if (d?.url) {
        const ir = await fetch(d.url);
        buf = Buffer.from(await ir.arrayBuffer());
      }
      if (!buf) throw new Error("no image payload: " + txt.slice(0, 300));
      fs.writeFileSync(dest, buf);
      manifest[item.name] = { file: path.basename(dest), model, size, prompt: item.prompt, ms: Date.now() - t0, bytes: buf.length };
      fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 1));
      console.log(`[ok] ${item.name} ${(buf.length / 1024).toFixed(0)}KB ${((Date.now() - t0) / 1000).toFixed(1)}s`);
      return;
    } catch (e) {
      console.log(`[retry ${attempt}] ${item.name}: ${e.message}`);
      await new Promise((r) => setTimeout(r, 2500 * attempt));
    }
  }
  console.log(`[FAIL] ${item.name}`);
}

const queue = [...items];
const workers = Array.from({ length: Math.min(conc, queue.length) }, async () => {
  while (queue.length) {
    const it = queue.shift();
    await genOne(it);
  }
});
await Promise.all(workers);
console.log("done", Object.keys(manifest).length, "in manifest");
