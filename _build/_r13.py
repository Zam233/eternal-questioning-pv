# -*- coding: utf-8 -*-
import json
d = json.load(open('shots_v20.json', encoding='utf-8'))
for s in d:
    for L in s.get('layers', []):
        if L.get('t') != 'type':
            continue
        c = L['cue']
        w = c.get('words') or []
        last = max([x['t0'] for x in w], default=None)
        if last is None:
            continue
        if c['t1'] - last < 0.50:
            print('R13 %.2f 「%s」 last=%.2f t1=%.2f hold=%.2f (shot t1 %.2f)' % (
                s['t0'], c['text'], last, c['t1'], c['t1'] - last, s['t1']))
