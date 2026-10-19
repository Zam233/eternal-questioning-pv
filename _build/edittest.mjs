// 试一下中继是否支持 /images/edits（图生图）
import fs from "node:fs";
const BASE = process.env.IMG_BASE, KEY = process.env.IMG_KEY;
const src = process.argv[2] || "K:/5A大作/_ref/marx_ref.png";
const out = process.argv[3] || "_edittest.png";

const buf = fs.readFileSync(src);
const fd = new FormData();
fd.append("model", "gpt-image-2.5");
fd.append("image", new Blob([buf], { type: "image/png" }), "ref.png");
fd.append("prompt",
  "Turn this photograph into a cut-out layer for a monochrome film: 19th-century steel engraving / aquatint of the same man, same pose and likeness, isolated on a fully transparent background, no backdrop, no chair, no border, dense cross-hatching, paper grain, sharp torn silhouette edge, extreme chiaroscuro with one hard key light from the upper left.");
fd.append("size", "1024x1024");
fd.append("background", "transparent");
fd.append("response_format", "b64_json");

const r = await fetch(BASE + "/images/edits", {
  method: "POST",
  headers: { Authorization: "Bearer " + KEY },
  body: fd,
});
const t = await r.text();
console.log("status", r.status, "len", t.length);
if (!r.ok) { console.log(t.slice(0, 600)); process.exit(1); }
const d = JSON.parse(t).data?.[0];
if (d?.b64_json) { fs.writeFileSync(out, Buffer.from(d.b64_json, "base64")); console.log("saved", out); }
else console.log(JSON.stringify(d).slice(0, 300));
