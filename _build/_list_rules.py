# -*- coding: utf-8 -*-
import re
s = open('audit.py', encoding='utf-8').read()
for m in re.finditer(r'r\.(ok|fail|warn)\("(R\d\d)",\s*"([^"]{0,50})', s):
    print(m.group(2), m.group(1), m.group(3))
