# -*- coding: utf-8 -*-
import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else 'shots_v19.json'
d = json.load(open(path, encoding='utf-8'))
shots = d['shots'] if isinstance(d, dict) else d
s = shots[47]
def keys(x, ind=0):
    for k, v in x.items():
        if isinstance(v, dict):
            print(' '*ind + k + ' (dict)')
            keys(v, ind+2)
        elif isinstance(v, list):
            print(' '*ind + k + ' (list %d)' % len(v))
            if v and isinstance(v[0], dict):
                keys(v[0], ind+2)
        else:
            print(' '*ind + '%s = %r' % (k, v))
keys(s)
