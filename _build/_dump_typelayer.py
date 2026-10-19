# -*- coding: utf-8 -*-
import json, sys
path = sys.argv[1]
si = int(sys.argv[2])
d = json.load(open(path, encoding='utf-8'))
shots = d['shots'] if isinstance(d, dict) else d
s = shots[si]
for j, L in enumerate(s.get('layers', [])):
    if L.get('t') != 'type':
        continue
    print('--- type layer', j, 'keys:', sorted(L.keys()))
    for k, v in L.items():
        if isinstance(v, list):
            print('   %s: list %d' % (k, len(v)))
            for e in v[:3]:
                print('      ', json.dumps(e, ensure_ascii=False)[:400])
        elif isinstance(v, dict):
            print('   %s: dict %s' % (k, json.dumps(v, ensure_ascii=False)[:400]))
        else:
            print('   %s = %r' % (k, v))
