# -*- coding: utf-8 -*-
"""Compare every type cue in shots against lines.json (ASR-aligned truth)."""
import json

shots = json.load(open('shots_v19.json', encoding='utf-8'))
lines = json.load(open('lines.json', encoding='utf-8'))
by_text = {}
for L in lines:
    by_text.setdefault(L['text'], []).append(L)

rows = []
for i, s in enumerate(shots):
    for L in s.get('layers', []):
        if L.get('t') != 'type':
            continue
        c = L.get('cue') or {}
        txt = c.get('text', '')
        cands = by_text.get(txt) or []
        if not cands:
            rows.append((i, txt, c.get('t0'), c.get('t1'), None, None, 'NO-LINE'))
            continue
        # nearest candidate in time
        best = min(cands, key=lambda z: abs(z['t0'] - c.get('t0', 0)))
        rows.append((i, txt, c.get('t0'), c.get('t1'), best['t0'], best['t1'],
                     best['t0'] - c.get('t0', 0)))

for r in rows:
    d = r[6]
    flag = ''
    if isinstance(d, float):
        flag = 'OK ' if abs(d) <= 0.35 else ('EARLY %+.2f' % d if d > 0 else 'LATE %+.2f' % d)
    print('%2d %-14s cue %7.2f-%7.2f  line %s  %s' % (
        r[0], r[1], r[2], r[3],
        ('%7.2f-%7.2f' % (r[4], r[5])) if r[4] is not None else '     ---     ', flag))
