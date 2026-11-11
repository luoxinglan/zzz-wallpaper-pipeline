# -*- coding: utf-8 -*-
"""v36 final apply: results -> scene(3 layers) + project(full-range sliders, switches) + config."""
import os, json, sys, copy

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
CFG = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\config.json"
BK = os.path.join(HERE, "backup")

SINGLES = {7,8,9,11,12,16,17,18,20,21,25,27,30,32,34,35,37,41,42,44,45,47,49,52,53,55,57,58,59,61,63,67}
DISABLED = {26}

def hex2f(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

def fmt(rgb):
    return "%.5f %.5f %.5f" % rgb

def atomic(path, data):
    tmp = path + ".tmp"
    open(tmp, "w", encoding="utf-8").write(data)
    os.replace(tmp, path)

def find_proj(nn):
    pref = "zzz_mindscape_%02d_" % nn
    for d in os.listdir(BASE):
        if d.startswith(pref):
            return os.path.join(BASE, d)

def apply(nn, res):
    proj = find_proj(nn)
    single = nn in SINGLES
    disabled = nn in DISABLED
    vals = dict(ax=res['ax'], ay=res['ay'], bx=res['ax'] if single else res['bx'],
                by=res['ay'] if single else res['by'], r=res['r_pct'],
                cola=res['color_a'], colb=res['color_a'] if single else res['color_b'],
                ona=not disabled, onb=(not disabled and not single), enabled=not disabled)
    sp = os.path.join(proj, 'scene.json')
    sc = json.load(open(sp, encoding='utf-8'))
    for o in sc.get('objects', []):
        if o.get('name') not in ('bg1', 'bg2', 'bg3'):
            continue
        for e in (o.get('effects') or []):
            if e.get('name') == 'pupils':
                csv = e['passes'][0]['constantshadervalues']
                csv['眼A水平(%)']['value'] = vals['ax']; csv['眼A垂直(%)']['value'] = vals['ay']
                csv['眼B水平(%)']['value'] = vals['bx']; csv['眼B垂直(%)']['value'] = vals['by']
                csv['瞳孔半径(层高%)']['value'] = vals['r']
                csv['脉动颜色A']['value'] = fmt(hex2f(vals['cola']))
                csv['脉动颜色B']['value'] = fmt(hex2f(vals['colb']))
                csv['眼A开关'] = {"user": "pupulseona", "value": bool(vals['ona'])}
                csv['眼B开关'] = {"user": "pupulseonb", "value": bool(vals['onb'])}
        if o.get('name') == 'bg1':
            pass
    sc['objects'] = sc['objects']  # keep order
    # also set pupulse master switch off for disabled
    atomic(sp, json.dumps(sc, ensure_ascii=False, indent='\t'))
    pp = os.path.join(proj, 'project.json')
    pr = json.load(open(pp, encoding='utf-8'))
    props = pr['general']['properties']
    for k, v in (('pupulseax', vals['ax']), ('pupulseay', vals['ay']),
                 ('pupulsebx', vals['bx']), ('pupulseby', vals['by'])):
        props[k]['value'] = v
        props[k]['min'] = 0; props[k]['max'] = 100; props[k]['step'] = 0.1
    props['pupulsesize']['value'] = vals['r']
    props['pupulsesize']['min'] = 0.2; props['pupulsesize']['max'] = 8; props['pupulsesize']['step'] = 0.02
    props['pupulsecola']['value'] = fmt(hex2f(vals['cola']))
    props['pupulsecolb']['value'] = fmt(hex2f(vals['colb']))
    props['pupulseona']['value'] = 1 if vals['ona'] else 0
    props['pupulseonb']['value'] = 1 if vals['onb'] else 0
    props['pupulse']['value'] = vals['enabled']
    atomic(pp, json.dumps(pr, ensure_ascii=False, indent='\t'))
    return vals

def main():
    allvals = {}
    for f in sorted(os.listdir(RES)):
        if not f.endswith('.json'):
            continue
        res = json.load(open(os.path.join(RES, f), encoding='utf-8'))
        allvals[res['nn']] = apply(res['nn'], res)
    # config
    cfg = json.load(open(CFG, encoding='utf-8'))
    mon0 = cfg['25485']['general']['wallpaperconfig']['selectedwallpapers']['Monitor0']
    if 'playlist' in mon0:
        del mon0['playlist']
    wp = cfg['25485']['wproperties']
    for nn, vals in allvals.items():
        key = find_proj(nn).replace(os.sep, '/') + '/scene.json'
        mon = wp.setdefault(key, {}).setdefault('Monitor0', {})
        mon['pupulseax'] = vals['ax']; mon['pupulseay'] = vals['ay']
        mon['pupulsebx'] = vals['bx']; mon['pupulseby'] = vals['by']
        mon['pupulsesize'] = vals['r']
        mon['pupulsecola'] = vals['cola']; mon['pupulsecolb'] = vals['colb']
        mon['pupulseona'] = 'true' if vals['ona'] else 'false'
        mon['pupulseonb'] = 'true' if vals['onb'] else 'false'
        mon['pupulse'] = 'true' if vals['enabled'] else 'false'
    atomic(CFG, json.dumps(cfg, ensure_ascii=False, indent='\t'))
    back = json.load(open(CFG, encoding='utf-8'))
    key = find_proj(1).replace(os.sep, '/') + '/scene.json'
    m = back['25485']['wproperties'][key]['Monitor0']
    print("config OK, sample 01:", m['pupulseax'], m['pupulseay'], m['pupulseona'], m['pupulseonb'])

if __name__ == '__main__':
    main()
