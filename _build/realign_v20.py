# -*- coding: utf-8 -*-
"""v20: re-time the 3:37-4:05 cues to the real vocal (lines.json / whisper word
timestamps), and rebuild "你看啊" so the three glyphs sit on one clean line.

Root cause of the drift: PV_文字分镜表.md carried hand-estimated windows for
shots 39/41 ("那是直面未知" 217.3-219.5, "你看啊" 229.1-231.5) while the vocal
actually sings them at 219.94-222.48 and 232.58-234.74.  Everything downstream
(per-char `words`, per-glyph `at`, shot `_cue_end`, one camera beat) inherited
the wrong anchors, so the text led the voice by 1.9 s / 3.1 s.
"""
import json
import bisect

SRC = 'shots_v19.json'
DST = 'shots_v20.json'

shots = json.load(open(SRC, encoding='utf-8'))
lines = json.load(open('lines.json', encoding='utf-8'))
grid = json.load(open('beat_grid.json', encoding='utf-8'))['beats']
B8 = sorted(grid + [(a + b) / 2.0 for a, b in zip(grid, grid[1:])])


def snap(t_abs, tol=0.12):
    i = bisect.bisect_left(B8, t_abs)
    cand = [B8[j] for j in (i - 1, i) if 0 <= j < len(B8)]
    if not cand:
        return t_abs
    best = min(cand, key=lambda b: abs(b - t_abs))
    return best if abs(best - t_abs) <= tol else t_abs


def line_of(text):
    hits = [L for L in lines if L['text'] == text]
    if not hits:
        raise SystemExit('no line for %r' % text)
    return hits[0]


def find_cue(text):
    for s in shots:
        for L in s.get('layers', []):
            if L.get('t') == 'type' and (L.get('cue') or {}).get('text') == text:
                return s, L['cue']
    raise SystemExit('no cue for %r' % text)


def retime(text, t0=None, t1=None, stamps=None):
    s, c = find_cue(text)
    ln = line_of(text)
    wt = [w['t0'] for w in ln['words']]
    c['t0'] = round(ln['t0'] if t0 is None else t0, 3)
    c['t1'] = round(ln['t1'] if t1 is None else t1, 3)
    n = len(c['text'])
    words = c.get('words') or []
    while len(words) < n:
        words.append({'t0': c['t0']})
    for i in range(n):
        words[i]['t0'] = round(wt[i] if i < len(wt) else c['t0'] + 0.08 * i, 3)
    c['words'] = words[:n]
    gs = c.get('glyph') or []
    for i, g in enumerate(gs[:n]):
        g['at'] = round(stamps if stamps is not None else c['words'][i]['t0'], 3)
    print('  %-14s %7.2f-%7.2f  words %s' % (text, c['t0'], c['t1'],
                                             [w['t0'] for w in c['words']]))
    return s, c


# ---- 39a 那是直面未知 : vocal 219.94-222.48, hold the last char to 222.54
retime('那是直面未知', t0=219.94, t1=222.54)

# ---- 39b 向死而生 : stamp, all four land together on the first sung syllable
retime('向死而生', t0=222.48, t1=224.28, stamps=222.48)

# ---- 40 自由自觉的坚韧灵魂啊 : 224.02-229.44
retime('自由自觉的坚韧灵魂啊', t0=224.02, t1=229.44)

# ---- 41 你看啊 : 232.58-234.74, three glyphs on one clean line
s50, c50 = retime('你看啊', t0=232.58, t1=235.10)
c50['layout'] = 'center'
c50['band'] = 0.5
c50['stagger'] = 0.0
for g in c50.get('glyph') or []:
    g['s'] = 2.0
    g['dy'] = 0.0
    g['dx'] = 0.0
    g['r'] = 0.0

# ---- 42a 真理之光终会抵达 : 236.12-240.16
retime('真理之光终会抵达', t0=236.12, t1=240.16)

# ---- 42b 请务必再追问一下 : 240.16-245.12
retime('请务必再追问一下', t0=240.16, t1=244.95)

# ---- one camera pose in shot 48 was anchored to the old (wrong) cue start
s48 = [s for s in shots if abs(s['t0'] - 217.26) < 0.01][0]
t_new = snap(219.94)
for b in s48['cam']['beats']:
    if abs(float(b['t']) - 0.80) < 0.02:
        b['t'] = round(t_new - s48['t0'], 3)
for a in s48['cam']['accents']:
    if abs(float(a['t']) - 0.829) < 0.02:
        a['t'] = round(t_new - s48['t0'], 3)
print('  shot48 beat -> %.3f (local %.3f)' % (t_new, t_new - s48['t0']))

# ---- shot _cue_end = max cue t1
for s in shots:
    ts = [(L.get('cue') or {}).get('t1') for L in s.get('layers', []) if L.get('t') == 'type']
    ts = [t for t in ts if isinstance(t, float)]
    if ts:
        s['_cue_end'] = round(max(ts), 3)

json.dump(shots, open(DST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote', DST)
