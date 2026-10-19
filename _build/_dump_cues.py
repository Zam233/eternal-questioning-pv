# -*- coding: utf-8 -*-
"""Dump cues (one per type layer) in a time window with per-char timings."""
import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else 'shots_v19.json'
t0 = float(sys.argv[2]) if len(sys.argv) > 2 else 205.0
t1 = float(sys.argv[3]) if len(sys.argv) > 3 else 240.0

d = json.load(open(path, encoding='utf-8'))
shots = d['shots'] if isinstance(d, dict) else d
for i, s in enumerate(shots):
    a = s.get('t0', 0); b = s.get('t1', 0)
    if not (b > t0 and a < t1):
        continue
    print('== SHOT %d  %.2f-%.2f  cue_end=%s' % (i, a, b, s.get('_cue_end')))
    for L in s.get('layers', []):
        if L.get('t') != 'type':
            continue
        c = L.get('cue') or {}
        w = [round(x.get('t0', 0), 2) for x in c.get('words', [])]
        txt = c.get('text', '')
        print('   [%s] %-14r %7.2f-%7.2f lay=%s ay=%s band=%s z=%s' % (
            c.get('kind'), txt, c.get('t0', 0), c.get('t1', 0),
            c.get('layout'), c.get('anchor_y'), c.get('band'), L.get('z')))
        print('        words %s' % w)
        segs = c.get('segs')
        if segs:
            print('        segs  %s' % json.dumps(segs, ensure_ascii=False)[:300])
        gs = c.get('glyph') or []
        if gs:
            print('        glyph %s' % ' '.join('%s:%.2f@%s' % (g.get('ch'), g.get('s', 1), round(g.get('at', 0), 2)) for g in gs))
