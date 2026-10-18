# -*- coding: utf-8 -*-
"""Renumber every PLATE caption in make_v14.py by its order in the file."""
import io
import re

p = "make_v14.py"
s = io.open(p, encoding="utf-8").read()
pat = re.compile(r'no="PLATE \d+"')
ms = list(pat.finditer(s))
print("found", len(ms))
out, last = [], 0
for i, m in enumerate(ms):
    out.append(s[last:m.start()])
    out.append('no="PLATE %02d"' % (i + 1))
    last = m.end()
out.append(s[last:])
s2 = "".join(out)
io.open(p, "w", encoding="utf-8", newline="").write(s2)
ms2 = list(pat.finditer(s2))
print("now", len(ms2), "last", ms2[-1].group(0) if ms2 else "-")
