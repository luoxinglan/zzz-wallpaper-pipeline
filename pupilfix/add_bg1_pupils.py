# -*- coding: utf-8 -*-
"""Add pupils effect instance to bg1 for all zzz_mindscape projects."""
import json, os, sys

BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
HERE = os.path.dirname(os.path.abspath(__file__))

def atomic(path, data):
    tmp = path + ".tmp"
    open(tmp, "w", encoding="utf-8").write(data)
    os.replace(tmp, path)

n_add = n_skip = 0
for d in sorted(os.listdir(BASE)):
    if not d.startswith('zzz_mindscape_'):
        continue
    p = os.path.join(BASE, d)
    sp = os.path.join(p, 'scene.json')
    sc = json.load(open(sp, encoding='utf-8'))
    objs = {o.get('name'): o for o in sc.get('objects', [])}
    bg1, bg3 = objs.get('bg1'), objs.get('bg3')
    if bg1 is None or bg3 is None:
        print(d, 'MISSING bg layers'); continue
    src = None
    for e in (bg3.get('effects') or []):
        if e.get('name') == 'pupils':
            src = e
    if src is None:
        print(d, 'no pupils on bg3?!'); continue
    effs = bg1.get('effects') or []
    if any(e.get('name') == 'pupils' for e in effs):
        n_skip += 1
        continue
    import copy
    inst = copy.deepcopy(src)
    # unique id
    used = set()
    def collect(o):
        if isinstance(o, dict):
            if 'id' in o and isinstance(o['id'], int):
                used.add(o['id'])
            for v in o.values(): collect(v)
        elif isinstance(o, list):
            for v in o: collect(v)
    collect(sc)
    inst['id'] = max(used) + 1
    inst['visible'] = True
    bg1['effects'] = effs + [inst]
    atomic(sp, json.dumps(sc, ensure_ascii=False, indent='\t'))
    n_add += 1
print('added:', n_add, 'already-present:', n_skip)

# verify all three layers carry pupils with identical values
bad = []
for d in sorted(os.listdir(BASE)):
    if not d.startswith('zzz_mindscape_'):
        continue
    p = os.path.join(BASE, d)
    sc = json.load(open(os.path.join(p, 'scene.json'), encoding='utf-8'))
    per = {}
    for o in sc.get('objects', []):
        for e in (o.get('effects') or []):
            if e.get('name') == 'pupils':
                csv = e['passes'][0]['constantshadervalues']
                per[o['name']] = (csv['眼A水平(%)']['value'], csv['眼B水平(%)']['value'])
    if len(per) != 3 or len(set(per.values())) != 1:
        bad.append((d, per))
print('verify:', 'OK 60x3 identical' if not bad else bad[:5])
