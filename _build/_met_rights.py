# -*- coding: utf-8 -*-
"""Ask the Met API whether each committed asset is Open Access / public domain."""
import json
import os
import subprocess
import sys

PROXY = "http://127.0.0.1:7897"
os.environ.setdefault("HTTPS_PROXY", PROXY)
os.environ.setdefault("HTTP_PROXY", PROXY)

ids = sorted({p.split('/')[-1].replace('.jpg', '')
              for p in subprocess.check_output(
                  ['git', 'ls-tree', '-r', 'origin/main', '--name-only'],
                  text=True).splitlines()
              if p.startswith('assets/met')})

import urllib.request


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'pv-license-check'})
    op = urllib.request.build_opener(urllib.request.ProxyHandler(
        {'http': PROXY, 'https': PROXY}))
    with op.open(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


out = []
for oid in ids:
    try:
        d = get('https://collectionapi.metmuseum.org/public/collection/v1/objects/' + oid)
        out.append({
            'id': oid,
            'title': d.get('title', '')[:70],
            'artist': (d.get('artistDisplayName') or '')[:40],
            'date': d.get('objectDate', '')[:30],
            'pd': d.get('isPublicDomain'),
            'rights': d.get('rightsAndReproduction', '')[:60],
        })
    except Exception as e:
        out.append({'id': oid, 'error': str(e)[:80]})

json.dump(out, open('_build/met_rights.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

n_pd = sum(1 for o in out if o.get('pd') is True)
n_no = sum(1 for o in out if o.get('pd') is False)
n_err = sum(1 for o in out if 'error' in o)
print('objects', len(out), 'public-domain', n_pd, 'NOT', n_no, 'errors', n_err)
for o in out:
    if o.get('pd') is not True:
        print(' ', o)
