// 用本地参考图做图生图抠像：node editgen.mjs <ref> <name> "<补充描述>"
import fs from "node:fs";
const BASE = process.env.IMG_BASE, KEY = process.env.IMG_KEY;
const [ref, name, desc = ""] = process.argv.slice(2);
const buf = fs.readFileSync(ref);

const fd = new FormData();
fd.append("model", "gpt-image-2.5");
fd.append("image", new Blob([buf], { type: "image/png" }), "ref.png");
fd.append("prompt",
  "Turn this reference portrait into a cut-out layer for a monochrome film: 19th-century steel engraving / aquatint of the SAME man, keeping his exact likeness, facial structure, hair and beard. " +
  "Ignore everything else in the reference: crop to head and shoulders of the central figure only, remove other people, background, hands and props. " +
  desc + " " +
  "Isolated on a fully transparent background, no backdrop, no frame, no border, no text; dense cross-hatching, paper grain, sharp torn silhouette edge, extreme chiaroscuro with one hard key light from the upper left, the far side going to black. Monochrome only.");
fd.append("size", "1024x1024");
fd.append("background", "transparent");
fd.append("response_format", "b64_json");

const out = `_gen_${name}.png`;
for (let att = 1; att <= 3; att++) {
  const res = await fetch(BASE + "/images/edits", {
    method: "POST", headers: { Authorization: "Bearer " + KEY }, body: fd,
  });
  const t = await res.text();
  if (!res.ok) { console.log("attempt", att, "HTTP", res.status, t.slice(0, 200)); continue; }
  const d = JSON.parse(t).data?.[0];
  if (d?.b64_json) { fs.writeFileSync(out, Buffer.from(d.b64_json, "base64")); console.log("ok", out); process.exit(0); }
}
process.exit(1);
