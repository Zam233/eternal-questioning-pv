// Download a wheel file from a PEP 503 index entry (resolves the real URL).
import fs from "node:fs";
import path from "node:path";

const pkg = process.argv[2];          // e.g. cupy-cuda12x
const want = process.argv[3];         // filename substring, e.g. cp314-cp314-win_amd64
const outDir = process.argv[4] || "_tmp/wheels";
fs.mkdirSync(outDir, { recursive: true });

const index = `https://pypi.tuna.tsinghua.edu.cn/simple/${pkg}/`;
const r = await fetch(index, { headers: { "user-agent": "pip/25" } });
const html = await r.text();

const rows = [...html.matchAll(/<a[^>]+href="([^"]+)"[^>]*>([^<]+\.whl)<\/a>/g)]
  .map((m) => ({ href: m[1], name: m[2] }))
  .filter((x) => x.name.includes(want));

if (!rows.length) { console.log("no match for", pkg, want); process.exit(1); }
// newest version last on most indexes; take the last match
const pick = rows[rows.length - 1];
let href = pick.href;
if (href.startsWith("../../")) href = "https://pypi.tuna.tsinghua.edu.cn/" + href.slice(6);
if (href.startsWith("/")) href = "https://pypi.tuna.tsinghua.edu.cn" + href;

const dest = path.join(outDir, pick.name);
if (fs.existsSync(dest) && fs.statSync(dest).size > 1e6) {
  console.log("already have", dest, (fs.statSync(dest).size / 1048576).toFixed(0) + "MB");
  process.exit(0);
}
console.log("downloading", pick.name, "from", href.slice(0, 90));
const res = await fetch(href, { headers: { "user-agent": "pip/25" } });
if (!res.ok) { console.log("HTTP", res.status); process.exit(1); }
const buf = Buffer.from(await res.arrayBuffer());
fs.writeFileSync(dest, buf);
console.log("saved", dest, (buf.length / 1048576).toFixed(1) + "MB");
