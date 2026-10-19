# -*- coding: utf-8 -*-
import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else 'shots_v19.json'
t0 = float(sys.argv[2]) if len(sys.argv) > 2 else 212.0
t1 = float(sys.argv[3]) if len(sys.argv) > 3 else 226.0

d = json.load(open(path, encoding='utf-8'))
shots = d['shots'] if isinstance(d, dict) else d
print('type', type(d).__name__, 'n', len(shots))
for i, s in enumerate(shots):
    a = s.get('t0', 0); b = s.get('t1', 0)
    if b > t0 and a < t1:
        print('SHOT %d  %.2f-%.2f  %s' % (i, a, b, s.get('id')))
        for c in s.get('cues', []):
            print('   CUE %7.2f-%7.2f  %-28r layout=%s anchor_y=%s band=%s' % (
                c.get('t0', 0), c.get('t1', 0), c.get('text'),
                c.get('layout'), c.get('anchor_y'), c.get('band')))
