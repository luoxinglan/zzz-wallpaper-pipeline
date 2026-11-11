# -*- coding: utf-8 -*-
"""Analyze which layer (bg1/bg2/bg3) is visible at each project's eye position."""
import json, os, math

CFG = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\config.json"
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
RD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

cfg = json.load(open(CFG, encoding='utf-8'))
wp = cfg['25485']['wproperties']

def region_of(uvx, uvy, ang1, off1, ang2, off2, H=2269.0, W=4128.0):
    px = (uvx / 100 - 0.5) * W
    py = (uvy / 100 - 0.5) * H
    def normal(a):
        r = math.radians(a + 90)
        return (math.cos(r), math.sin(r))
    n1 = normal(ang1); n2 = normal(ang2)
    d1 = off1 * 5.4; d2 = off2 * 5.4
    s1 = px * n1[0] + py * n1[1] - d1
    s2 = px * n2[0] + py * n2[1] + d2
    if s1 > 0: return "up"
    if s2 < 0: return "low"
    return "mid"

summary = []
for d in sorted(os.listdir(BASE)):
    if not d.startswith('zzz_mindscape_'):
        continue
    nn = int(d.split('_')[2])
    p = os.path.join(BASE, d)
    key = p.replace(os.sep, '/') + '/scene.json'
    mon = wp.get(key, {}).get('Monitor0', {})
    pr = json.load(open(os.path.join(p, 'project.json'), encoding='utf-8'))
    props = pr['general']['properties']

    def gv(name):
        v = mon.get(name)
        if v is None:
            v = props.get(name, {}).get('value')
        return v

    f = {i: bool(gv('_%d' % i)) for i in range(1, 7)}
    modes = {}
    if f[4] or f[5] or f[6]:
        if f[4] and not f[5] and not f[6]: modes['3'] = '1'
        elif f[4] and f[5] and not f[6]: modes['3'] = '12'
        elif f[4] and not f[5] and f[6]: modes['3'] = '13'
        elif not f[4] and f[5] and not f[6]: modes['3'] = '2'
        elif not f[4] and f[5] and f[6]: modes['3'] = '23'
        elif not f[4] and not f[5] and f[6]: modes['3'] = '3'
        elif f[4] and f[5] and f[6]: modes['3'] = '0'
    if (f[1] or f[2] or f[3]) and ((f[1] and not f[4]) or (f[2] and not f[5]) or (f[3] and not f[6])):
        c1 = f[1] and not f[4]; c2 = f[2] and not f[5]; c3 = f[3] and not f[6]
        if c1 and not c2 and not c3: modes['2'] = '1'
        elif c1 and c2 and not c3: modes['2'] = '12'
        elif c1 and not c2 and c3: modes['2'] = '13'
        elif not c1 and c2 and not c3: modes['2'] = '2'
        elif not c1 and c2 and c3: modes['2'] = '23'
        elif not c1 and not c2 and c3: modes['2'] = '3'
        elif c1 and c2 and c3: modes['2'] = '0'
    if not ((f[1] or f[4]) and (f[2] or f[5]) and (f[3] or f[6])):
        modes['1'] = ''

    masktype = gv('masktype')
    sc = json.load(open(os.path.join(p, 'scene.json'), encoding='utf-8'))
    masks = {}
    for o in sc.get('objects', []):
        for e in (o.get('effects') or []):
            nm = e.get('name', '')
            for mode in modes:
                if nm == 'mask%s_%s' % (mode, masktype):
                    csv = e['passes'][0]['constantshadervalues']
                    def resolve(k):
                        v = csv.get(k)
                        if isinstance(v, dict) and 'user' in v:
                            return gv(v['user'])
                        if isinstance(v, dict):
                            return v.get('value')
                        return v
                    masks[mode] = dict(
                        ang1=resolve('边1倾角'), off1=resolve('边1偏移(%)'),
                        ang2=resolve('边2倾角'), off2=resolve('边2偏移(%)'),
                        zm=resolve('区域-中间(1/4)'), zu=resolve('区域-线上(2/5)'),
                        zl=resolve('区域-线下(3/6)'))

    ax = gv('pupulseax'); ay = gv('pupulseay')
    bx = gv('pupulsebx'); by = gv('pupulseby')
    lay = {}
    for mode, prm in masks.items():
        if prm['ang1'] is None:
            continue
        info = {}
        for tag, (ex, ey) in (('A', (ax, ay)), ('B', (bx, by))):
            reg = region_of(ex, ey, prm['ang1'], prm['off1'], prm['ang2'], prm['off2'])
            zf = {'mid': prm['zm'], 'up': prm['zu'], 'low': prm['zl']}[reg]
            vis = zf is not None and float(zf) > 0.5
            info[tag] = (reg, vis)
        lay[mode] = info
    summary.append((nn, d.split('_', 3)[3], modes, masktype, lay))
    print(nn, d.split('_', 3)[3], '| modes:', modes, 'masktype:', masktype, '| eye:', lay)

# count projects where eye visible on NO active layer
bad = [s for s in summary if s[4] and not any(v['A'][1] for v in s[4].values())]
print()
print('projects where eye A NOT visible on any layer:', len(bad))
for s in bad: print('  ', s[0], s[1], s[4])
