# -*- coding: utf-8 -*-
"""Dump type layers (with cue text/timings) in a time window."""
import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else 'shots_v19.json'
t0 = float(sys.argv[2]) if len(sys.argv) > 2 else 210.0
t1 = float(sys.argv[3]) if len(sys.argv) > 3 else 230.0

d = json.load(open(path, encoding='utf-8'))
shots = d['shots'] if isinstance(d, dict) else d
for i, s in enumerate(shots):
    a = s.get('t0', 0); b = s.get('t1', 0)
    if not (b > t0 and a < t1):
        continue
    print('== SHOT %d  %.2f-%.2f  pal=%s' % (i, a, b, s.get('palette')))
    for L in s.get('layers', []):
        t = L.get('t')
        if t != 'type':
            print('   layer %-8s src=%s z=%s' % (t, L.get('src'), L.get('z')))
            continue
        print('   TYPE anchors: layout=%s band=%s anchor_y=%s' % (L.get('layout'), L.get('band'), L.get('anchor_y')))
        for c in L.get('cues', []):
            print('      CUE %7.2f-%7.2f  %-16r layout=%s ay=%s band=%s' % (
                c.get('t0', 0), c.get('t1', 0), c.get('text'),
                c.get('layout'), c.get('anchor_y'), c.get('band')))
