# -*- coding: utf-8 -*-
"""Build a single-file per-character timing tool (timing_tool.html).

The tool embeds the lyric lines + current timings, plays the mp3, and lets you
stamp each glyph's onset by ear. It exports timing_manual.json, which the
renderer prefers over lines.json.
"""
import json, io, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "timing_tool.html")

lines = json.load(io.open(os.path.join(HERE, "lines.json"), encoding="utf-8"))
DROP = {"\u8fa9\u9a73\u91cc\u6709\u8c01\u5c06\u4fe1\u4ef0", "\u60df\u6709\u76f4\u9762\u8352\u8c2c\u51b3\u610f\u81ea\u51b3\u7684\u4f60\u6211"}
seen, kept = set(), []
for l in lines:
    t = l["text"].replace("\u201c", '"').replace("\u201d", '"').strip()
    if t in DROP:
        if t in seen:
            continue
        seen.add(t)
    l["text"] = t
    kept.append({"text": t, "section": l.get("section", ""), "t0": l["t0"], "t1": l["t1"],
                 "words": [{"c": w["c"], "t0": w["t0"], "t1": w["t1"]} for w in (l.get("words") or [])]})

DATA = json.dumps(kept, ensure_ascii=False)

HTML = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>逐字打点 · 追问一下</title>
<style>
:root{--bg:#111;--fg:#e8e2d4;--dim:#7d766a;--hi:#f2c46a;--line:#2a2723}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 "Noto Serif SC",serif;}
header{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;gap:16px;align-items:center;flex-wrap:wrap}
h1{font-size:15px;font-weight:600;margin:0;letter-spacing:.08em}
button{background:#1d1b18;color:var(--fg);border:1px solid #3a3630;padding:6px 12px;border-radius:4px;cursor:pointer;font:inherit}
button:hover{background:#2a2620}
button.on{background:var(--hi);color:#1a1613;border-color:var(--hi)}
#wrap{padding:16px 20px}
canvas{width:100%;height:130px;display:block;background:#171512;border:1px solid var(--line);border-radius:4px}
#phrase{margin:18px 0 6px;font-size:34px;letter-spacing:.06em}
#phrase .c{color:var(--dim);transition:color .08s}
#phrase .c.done{color:#cfc7b6}
#phrase .c.cur{color:var(--hi);text-shadow:0 0 16px rgba(242,196,106,.5)}
#meta{color:var(--dim);font-size:12px;letter-spacing:.06em}
.row{display:flex;gap:24px;flex-wrap:wrap;margin-top:10px;color:var(--dim);font-size:12px}
kbd{background:#22201c;border:1px solid #3a3630;border-radius:3px;padding:1px 6px;font-family:monospace;color:#cfc7b6}
#list{margin-top:18px;max-height:220px;overflow:auto;border-top:1px solid var(--line)}
#list div{padding:3px 0;color:var(--dim);font-size:12px;border-bottom:1px solid #1b1916}
#list div.cur{color:var(--hi)}
#list div.done{color:#a9a294}
</style></head><body>
<header>
  <h1>逐字打点 · 追问一下</h1>
  <button id="load">载入 mp3</button>
  <input id="file" type="file" accept="audio/*" style="display:none">
  <button id="play">播放 / 暂停</button>
  <button id="prev">上一字</button>
  <button id="next">确认 → 下一字</button>
  <button id="undo">回退</button>
  <button id="save">导出 timing_manual.json</button>
  <span id="prog" style="color:#7d766a;font-size:12px"></span>
  <label style="color:#7d766a;font-size:12px"><input type="checkbox" id="follow" checked> 跟随播放头</label>
</header>
<div id="wrap">
  <canvas id="wave"></canvas>
  <div id="phrase"></div>
  <div id="meta"></div>
  <div class="row">
    <span><kbd>空格</kbd> 播放/暂停</span>
    <span><kbd>←</kbd><kbd>→</kbd> ±1 帧</span>
    <span><kbd>Shift+←/→</kbd> ±0.25 秒</span>
    <span><kbd>Enter</kbd> 确认并跳下一字</span>
    <span><kbd>Backspace</kbd> 回退一字</span>
    <span><kbd>Home</kbd> 回到当前句起音</span>
  </div>
  <div id="list"></div>
</div>
<audio id="au" preload="auto"></audio>
<script>
const LINES = __DATA__;
const FPS = 48;               // snap grid = 1/48 s
let chars = [];               // flat list {li,ci,c,t0,cur}
let cursor = 0, au = document.getElementById('au'), ctx = document.getElementById('wave').getContext('2d');
let peaks = null, dur = 0;

LINES.forEach((L, li) => {
  const t0 = L.t0, t1 = L.t1;
  [...L.text].forEach((c, ci) => {
    const w = (L.words && L.words[ci]) || null;
    chars.push({ li, ci, c, t0: w ? w.t0 : t0 + (t1 - t0) * ci / Math.max(1, L.text.length), g: 0 });
  });
});

document.getElementById('load').onclick = () => document.getElementById('file').click();
document.getElementById('file').onchange = e => {
  const f = e.target.files[0]; if (!f) return;
  au.src = URL.createObjectURL(f);
  au.onloadedmetadata = () => { dur = au.duration; buildPeaks(); draw(); render(); };
};

function buildPeaks(){
  const ac = new (window.AudioContext||window.webkitAudioContext)();
  fetch(au.src).then(r=>r.arrayBuffer()).then(b=>ac.decodeAudioData(b)).then(buf=>{
    const ch = buf.getChannelData(0), N = 1400, step = Math.floor(ch.length/N);
    peaks = new Float32Array(N);
    for(let i=0;i<N;i++){ let m=0; for(let j=0;j<step;j+=8){ const v=Math.abs(ch[i*step+j]||0); if(v>m)m=v; } peaks[i]=m; }
    draw();
  }).catch(()=>{});
}

function draw(){
  const W = ctx.canvas.width = ctx.canvas.clientWidth*2;
  const H = ctx.canvas.height = 260;
  ctx.clearRect(0,0,W,H);
  if(peaks){
    const mid = H*0.52;
    for(let i=0;i<peaks.length;i++){
      const x = i/peaks.length*W, h = peaks[i]*H*0.46;
      ctx.fillStyle = '#3b362d'; ctx.fillRect(x, mid-h, Math.max(1,W/peaks.length-0.6), h*2);
    }
  }
  // time cursor
  if(dur){ const x = au.currentTime/dur*W; ctx.fillStyle='#f2c46a'; ctx.fillRect(x,0,2,H); }
  // phrase blocks
  LINES.forEach(L=>{
    if(!dur) return;
    const x0=L.t0/dur*W, x1=L.t1/dur*W;
    ctx.fillStyle='rgba(242,196,106,0.10)'; ctx.fillRect(x0,H*0.86,x1-x0,H*0.10);
  });
}
ctx.canvas.onclick = e => { if(!dur) return; const r=ctx.canvas.getBoundingClientRect();
  const f=(e.clientX-r.left)/r.width; au.currentTime=f*dur; draw(); render(); };

function curChar(){ return chars[Math.min(cursor, chars.length-1)]; }
function frameSnap(t){ return Math.round(t*FPS)/FPS; }

function render(){
  const cc = curChar(); if(!cc) return;
  const L = LINES[cc.li];
  document.getElementById('phrase').innerHTML = [...L.text].map((c,i)=>
    `<span class="c ${i<cc.ci?'done':(i===cc.ci?'cur':'')}">${c}</span>`).join('');
  document.getElementById('meta').textContent =
    `第 ${cc.li+1}/${LINES.length} 句 · 第 ${cc.ci+1} 字 · 当前时码 ${frameSnap(au.currentTime||0).toFixed(3)}s · 段 ${L.section||'—'}`;
  document.getElementById('prog').textContent = `${cursor}/${chars.length} 字已确认`;
  const list = document.getElementById('list');
  list.innerHTML = '';
  LINES.forEach((l,li)=>{
    const d=document.createElement('div');
    d.className = li<cc.li?'done':(li===cc.li?'cur':'');
    d.textContent = `${String(li+1).padStart(2,'0')}  ${l.t0.toFixed(2)}  ${l.text}`;
    list.appendChild(d);
  });
  list.querySelectorAll('div')[cc.li]?.scrollIntoView({block:'nearest'});
  draw();
}

function stamp(){
  const cc = curChar(); if(!cc) return;
  cc.t0 = frameSnap(au.currentTime);
  cc.g = 1;
  cursor = Math.min(chars.length-1, cursor+1);
  render();
}
function back(){ cursor = Math.max(0, cursor-1); const cc=curChar(); if(cc&&cc.g){ cc.g=0; } render(); }
function seekTo(t){ au.currentTime = Math.max(0, t); draw(); render(); }

document.getElementById('play').onclick = ()=>{ au.paused?au.play():au.pause(); };
document.getElementById('next').onclick = stamp;
document.getElementById('undo').onclick = back;
document.getElementById('prev').onclick = ()=>{ cursor=Math.max(0,cursor-1); seekTo(curChar().t0); };
document.getElementById('save').onclick = ()=>{
  // rebuild lines with confirmed onsets; unconfirmed keep the original value
  const out = LINES.map((L,li)=>{
    const ws=[...L.text].map((c,ci)=>{
      const key = chars.find(x=>x.li===li&&x.ci===ci);
      return {c, t0:key.g?key.t0:(L.words&&L.words[ci]?L.words[ci].t0:L.t0), t1:0};
    });
    ws.forEach((w,i)=>{ w.t1 = i+1<ws.length? ws[i+1].t0 : (L.t1||w.t0+0.4); });
    return {text:L.text, section:L.section, t0:ws[0]?ws[0].t0:L.t0, t1:ws[ws.length-1]?ws[ws.length-1].t1:L.t1, words:ws};
  });
  const blob = new Blob([JSON.stringify(out,null,1)],{type:'application/json'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='timing_manual.json'; a.click();
};

addEventListener('keydown', e=>{
  if(e.code==='Space'){ e.preventDefault(); au.paused?au.play():au.pause(); return; }
  if(e.code==='ArrowRight'){ e.preventDefault(); seekTo(au.currentTime + (e.shiftKey?0.25:1/FPS)); }
  if(e.code==='ArrowLeft'){ e.preventDefault(); seekTo(au.currentTime - (e.shiftKey?0.25:1/FPS)); }
  if(e.code==='Enter'){ e.preventDefault(); stamp(); }
  if(e.code==='Backspace'){ e.preventDefault(); back(); }
  if(e.code==='Home'){ e.preventDefault(); seekTo(curChar()?LINES[curChar().li].t0:0); }
});

au.ontimeupdate = ()=>{ if(document.getElementById('follow').checked) draw(); };
requestAnimationFrame(function loop(){ if(!au.paused) draw(); requestAnimationFrame(loop); });

render();
</script></body></html>
"""

io.open(OUT, "w", encoding="utf-8").write(HTML.replace("__DATA__", DATA))
print("wrote", OUT, "chars:", sum(len(l["text"]) for l in kept), "lines:", len(kept))
