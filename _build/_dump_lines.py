# -*- coding: utf-8 -*-
import json, sys
d = json.load(open('lines.json', encoding='utf-8'))
t0 = float(sys.argv[1]) if len(sys.argv) > 1 else 195.0
t1 = float(sys.argv[2]) if len(sys.argv) > 2 else 250.0
for i, L in enumerate(d):
    if L['t1'] < t0 or L['t0'] > t1:
        continue
    print('%3d %7.2f-%7.2f  %-16s %s' % (i, L['t0'], L['t1'], L.get('section'), L['text']))
    print('     ', ' '.join('%s@%.2f' % (w['c'], w['t0']) for w in L.get('words', [])))
