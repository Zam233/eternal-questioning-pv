// Fetch public-domain images from the Met Open Access API (v1.1, paginated).
// Full-resolution primaryImage, saved to assets/met_full/<key>/<id>.jpg
// usage: node fetch_met.mjs [--per=3] [--only=key] [--resume]
import fs from "node:fs";
import path from "node:path";

const OUT = path.resolve("assets/met_full");
fs.mkdirSync(OUT, { recursive: true });
const args = process.argv.slice(2);
const flag = (n, d) => {
  const a = args.find((x) => x.startsWith(`--${n}=`));
  return a ? a.split("=").slice(1).join("=") : d;
};
const PER = parseInt(flag("per", "3"), 10);
const ONLY = flag("only", null);

const QUERIES = {
  plato: "plato philosopher",
  socrates: "death of socrates",
  hemlock: "cup goblet still life",
  cathedral: "gothic cathedral interior",
  celestial: "heavenly jerusalem celestial city",
  scriptorium: "monk writing manuscript",
  disputation: "scholars disputation",
  ruins: "ruins of antiquity",
  orrery: "clockwork mechanism orrery",
  optics: "eye optical diagram",
  tablet: "wax tablet writing slate",
  memento: "memento mori skull",
  stars: "celestial map star chart",
  pyramid: "pyramid egypt",
  industry: "industrial factory steam",
  forge: "blacksmith forge hammer",
  chains: "chained prisoner",
  market: "market scales coins",
  forest: "forest path trees",
  ladder: "ladder ascending",
  demolition: "ruined building collapse",
  prison: "prison cell interior",
  sisyphus: "sisyphus rock",
  dawn: "sunrise light rays",
  athens: "athens acropolis",
  latin: "medieval scholastic",
};

const manifestPath = path.join(OUT, "manifest.json");
const manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, "utf8")) : {};

const UA = { "user-agent": "dsh-pv/1.0 (research; contact: local)" };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function jget(u, tries = 5) {
  let wait = 2500;
  for (let i = 0; i < tries; i++) {
    const r = await fetch(u, { headers: UA });
    if (r.ok) return r.json();
    if (r.status === 403 || r.status === 429) {
      await sleep(wait);
      wait = Math.min(wait * 1.9, 20000);
      continue;
    }
    throw new Error("HTTP " + r.status + " " + u.slice(0, 80));
  }
  throw new Error("rate-limited " + u.slice(0, 80));
}

async function fetchKey(key, q) {
  const dir = path.join(OUT, key);
  fs.mkdirSync(dir, { recursive: true });
  const s = await jget(
    `https://collectionapi.metmuseum.org/public/collection/v1.1/search?q=${encodeURIComponent(q)}&hasImages=true&isPublicDomain=true&pageSize=40`
  );
  const ids = (s.objectIDs || []).slice(0, 40);
  let got = 0;
  for (const id of ids) {
    if (got >= PER) break;
    try {
      const o = await jget(`https://collectionapi.metmuseum.org/public/collection/v1/objects/${id}`);
      const url = o.primaryImage;
      if (!url || !o.isPublicDomain) continue;
      const dest = path.join(dir, `${id}.jpg`);
      if (!fs.existsSync(dest)) {
        const ir = await fetch(url, { headers: UA });
        if (!ir.ok) { await sleep(1200); continue; }
        const buf = Buffer.from(await ir.arrayBuffer());
        if (buf.length < 40000) { await sleep(600); continue; }
        fs.writeFileSync(dest, buf);
      }
      manifest[`${key}/${id}`] = {
        key, id, file: path.relative(OUT, dest), title: o.title, artist: o.artistDisplayName,
        date: o.objectDate, medium: o.medium, url,
      };
      got++;
      console.log(`[ok] ${key}/${id} ${(fs.statSync(dest).size / 1024).toFixed(0)}KB`);
      await sleep(700);
    } catch (e) {
      console.log(`[miss] ${key}/${id} ${e.message.slice(0, 60)}`);
      await sleep(1500);
    }
  }
  console.log(`[${got ? "done" : "EMPTY"}] ${key} -> ${got}`);
}

const keys = ONLY ? [ONLY] : Object.keys(QUERIES);
for (const k of keys) {
  if (!QUERIES[k]) { console.log("unknown key", k); continue; }
  const have = Object.keys(manifest).filter((m) => m.startsWith(k + "/")).length;
  if (have >= PER) { console.log(`[have] ${k} ${have}`); continue; }
  try { await fetchKey(k, QUERIES[k]); } catch (e) { console.log("[ERR]", k, e.message); }
  await sleep(900);
}
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 1));
console.log("total assets:", Object.keys(manifest).length);
