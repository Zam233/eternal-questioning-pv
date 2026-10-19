# -*- coding: utf-8 -*-
import json, sys
d = json.load(open('asr.json', encoding='utf-8'))
t0 = float(sys.argv[1]) if len(sys.argv) > 1 else 205.0
t1 = float(sys.argv[2]) if len(sys.argv) > 2 else 245.0
for seg in d['segments']:
    if seg['end'] < t0 or seg['start'] > t1:
        continue
    print('SEG %7.2f-%7.2f  %s' % (seg['start'], seg['end'], seg['text']))
    for w in seg.get('words', []):
        print('    %7.2f-%7.2f  %s' % (w['s'], w['e'], w['w']))
