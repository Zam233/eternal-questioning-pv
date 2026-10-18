import fs from "node:fs";
const BASE = process.env.IMG_BASE, KEY = process.env.IMG_KEY;
const r = await fetch(BASE + "/images/generations", {method:"POST",headers:{Authorization:"Bearer "+KEY,"Content-Type":"application/json"},body:JSON.stringify({model:"gpt-image-2.5",prompt:"a marble bust of a philosopher, dark engraved tonality",n:1,size:"1024x1024",quality:"high",response_format:"b64_json"})});
const t = await r.text();
console.log("status", r.status, t.length);
if (r.ok) { const d = JSON.parse(t).data[0]; if (d.b64_json) { fs.writeFileSync("_apitest.png", Buffer.from(d.b64_json,"base64")); console.log("saved", fs.statSync("_apitest.png").size); } else console.log(JSON.stringify(d).slice(0,200)); }
else console.log(t.slice(0,400));
