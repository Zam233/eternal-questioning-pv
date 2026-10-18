// Probe the OpenAI-compatible image endpoint.
const BASE = "https://api.tk1688.com/v1";
const KEY = process.env.IMG_KEY || "";

async function j(path, opts = {}) {
  const r = await fetch(BASE + path, {
    ...opts,
    headers: { Authorization: "Bearer " + KEY, "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  const txt = await r.text();
  let body;
  try { body = JSON.parse(txt); } catch { body = txt.slice(0, 800); }
  return { status: r.status, body };
}

const mode = process.argv[2] || "models";

if (mode === "models") {
  const r = await j("/models");
  console.log("status", r.status);
  const data = r.body?.data;
  if (Array.isArray(data)) {
    console.log("count", data.length);
    console.log(data.map((m) => m.id).filter((id) => /image|dall|gpt|flux|seedream|qwen|nano|kolors|mj/i.test(id)).join("\n"));
  } else {
    console.log(JSON.stringify(r.body).slice(0, 1500));
  }
}
