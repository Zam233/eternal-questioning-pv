# -*- coding: utf-8 -*-
import json
d = json.load(open('shots_v19.json', encoding='utf-8'))
for i in range(46, 53):
    s = d[i]
    print(i, '%.2f-%.2f' % (s['t0'], s['t1']), 'link', json.dumps(s.get('link')), 'cue_end', s.get('_cue_end'))
