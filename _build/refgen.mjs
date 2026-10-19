// 从 Wikimedia Commons 搜一张参考像并下载，然后用 /images/edits 生成同款铜版抠像。
// usage: node refgen.mjs <搜词> <输出名> "<风格/人物描述>"
import fs from "node:fs";

const BASE = process.env.IMG_BASE, KEY = process.env.IMG_KEY;
const q = process.argv[2];
const name = process.argv[3];
const desc = process.argv[4] || "";

const api = "https://commons.wikimedia.org/w/api.php?action=query&generator=search" +
  `&gsrsearch=${encodeURIComponent(q)}&gsrnamespace=6&gsrlimit=6&prop=imageinfo&iiprop=url|size&iiurlwidth=1200&format=json`;

const r = await fetch(api, { headers: { "User-Agent": "pv-bot/1.0 (research)" } });
const j = await r.json();
const pages = Object.values(j?.query?.pages || {});
pages.sort((a, b) => (b.imageinfo?.[0]?.width || 0) - (a.imageinfo?.[0]?.width || 0));
const cand = pages.find((p) => /\.(jpg|jpeg|png)$/i.test(p.title));
if (!cand) { console.error("no image for", q); process.exit(1); }
const url = cand.imageinfo[0].thumburl || cand.imageinfo[0].url;
console.log("ref:", cand.title, url);

const ir = await fetch(url, { headers: { "User-Agent": "pv-bot/1.0 (research)" } });
const buf = Buffer.from(await ir.arrayBuffer());
const refPath = `K:/5A大作/_ref/${name}_ref.png`;
fs.writeFileSync(refPath, buf);
console.log("saved ref", refPath, buf.length);

const fd = new FormData();
fd.append("model", "gpt-image-2.5");
fd.append("image", new Blob([buf], { type: "image/png" }), "ref.png");
fd.append("prompt",
  "Turn this reference portrait into a cut-out layer for a monochrome film: 19th-century steel engraving / aquatint of the SAME man, keeping his exact likeness, facial structure, hair and beard. " +
  desc + " " +
  "Isolated on a fully transparent background, no backdrop, no frame, no border, no text; dense cross-hatching, paper grain, sharp torn silhouette edge, extreme chiaroscuro with one hard key light from the upper left, the far side going to black. Monochrome only.");
fd.append("size", "1024x1024");
fd.append("background", "transparent");
fd.append("response_format", "b64_json");

const out = `_gen_${name}.png`;
for (let att = 1; att <= 2; att++) {
  const res = await fetch(BASE + "/images/edits", {
    method: "POST", headers: { Authorization: "Bearer " + KEY }, body: fd,
  });
  const t = await res.text();
  if (!res.ok) { console.log("attempt", att, "HTTP", res.status, t.slice(0, 200)); continue; }
  const d = JSON.parse(t).data?.[0];
  if (d?.b64_json) { fs.writeFileSync(out, Buffer.from(d.b64_json, "base64")); console.log("ok", out); process.exit(0); }
}
console.error("failed", name);
process.exit(1);
