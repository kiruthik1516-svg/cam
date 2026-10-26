import os
import re

endpoints = set()
for root, dirs, files in os.walk('facial-recognition-dashboard'):
    dirs[:] = [d for d in dirs if d not in ('node_modules', '.next', '.git')]
    for file in files:
        if file.endswith(('.ts', '.tsx')):
            p = os.path.join(root, file)
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                c = f.read()
            for m in re.finditer(r'[\'"`](/api/[^\'"`\? ]+)', c):
                endpoints.add(m.group(1))

for ep in sorted(endpoints):
    print(ep)

