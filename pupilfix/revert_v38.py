# -*- coding: utf-8 -*-
"""v38: revert to visible v2 shader, attach pupils to bg1+bg2+bg3 (mask-region coverage),
drop the v5 switch uniforms/properties, bg2-detected coords."""
import json, os, copy, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
BV3 = os.path.join(HERE, "backup_v3")
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
CFG = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\config.json"

def atomic(path, data):
    tmp = path + '.tmp'
    open(tmp, 'w', encoding='utf-8').write(data)
    os.replace(tmp, path)

def hex2f(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

def fmt(rgb):
    return "%.5f %.5f %.5f" % rgb

def find_proj(nn):
    pref = 'zzz_mindscape_%02d_' % nn
    for d in os.listdir(BASE):
        if d.startswith(pref):
            return os.path.join(BASE, d)

def build_csv(vals):
    return {
        "audioamount": {"user": "pupulseamt", "value": 1.0},
        "audiobounds": "-2 -1",
        "audioexponent": 3.0,
        "frequencymax": 1,
        "frequencymin": 0,
        "眼A水平(%)": {"user": "pupulseax", "value": vals['ax']},
        "眼A垂直(%)": {"user": "pupulseay", "value": vals['ay']},
        "眼B水平(%)": {"user": "pupulsebx", "value": vals['bx']},
        "眼B垂直(%)": {"user": "pupulseby", "value": vals['by']},
        "瞳孔半径(层高%)": {"user": "pupulsesize", "value": vals['r']},
        "脉动颜色A": {"user": "pupulsecola", "value": vals['cola']},
        "脉动颜色B": {"user": "pupulsecolb", "value": vals['colb']},
        "边缘柔化": {"user": "pupulsesoft", "value": 0.5},
    }

def main():
    allvals = {}
    for f in sorted(os.listdir(RES)):
        if not f.endswith('.json'):
            continue
        res = json.load(open(os.path.join(RES, f), encoding='utf-8'))
        nn = res['nn']
        proj = find_proj(nn)
        vals = dict(ax=res['ax'], ay=res['ay'], bx=res['bx'], by=res['by'],
                    r=res['r_pct'], cola=fmt(hex2f(res['color_a'])),
                    colb=fmt(hex2f(res['color_b'])))
        # 1) frag v2
        frag_src = os.path.join(BV3, '%02d' % nn, 'shaders', 'effects', 'pupils.frag')
        frag_dst = os.path.join(proj, 'shaders', 'effects', 'pupils.frag')
        frag_text = open(frag_src, encoding='utf-8').read()
        assert 'g_EnA' not in frag_text, nn
        open(frag_dst, 'w', encoding='utf-8', newline='').write(frag_text)
        # 2) scene
        sp = os.path.join(proj, 'scene.json')
        sc = json.load(open(sp, encoding='utf-8'))
        sc['objects'] = [o for o in sc['objects'] if o.get('name') != 'pupilglow']
        used = set()
        def collect(o):
            if isinstance(o, dict):
                if isinstance(o.get('id'), int):
                    used.add(o['id'])
                for v in o.values():
                    collect(v)
            elif isinstance(o, list):
                for v in o:
                    collect(v)
        collect(sc)
        nid = max(used) + 1
        csv = build_csv(vals)
        for o in sc['objects']:
            nm = o.get('name')
            if nm in ('bg1', 'bg2', 'bg3'):
                effs = [e for e in (o.get('effects') or [])
                        if e.get('name') not in ('pupils', 'pupilsoverlay')]
                inst = {"file": "effects/pupils/effect.json", "id": nid,
                        "name": "pupils",
                        "passes": [{"id": nid + 1, "combos": {"AUDIOPROCESSING": 3},
                                    "constantshadervalues": copy.deepcopy(csv)}],
                        "visible": True}
                nid += 2
                o['effects'] = effs + [inst]
            if nm == 'scripts':
                code = o.get('visible', {})
                if isinstance(code, dict) and 'script' in code:
                    s = code['script']
                    line = '    try { thisScene.getLayer("pupilglow").visible = !!engine.userProperties["pupulse"]; } catch (e) { }'
                    s = s.replace('\n' + line, '', 1)
                    if 'effect2.name === "pupils"' not in s:
                        OLD = """            layer.visible = true;
            if (engine.userProperties.parallax) {"""
                        NEW = """            layer.visible = true;
            for (let effect_id2 = 0; effect_id2 < layer.getEffectCount(); effect_id2++) {
                let effect2 = layer.getEffect(effect_id2);
                if (effect2.name === "pupils" && engine.userProperties["pupulse"]) {
                    effect2.visible = true;
                }
            }
            if (engine.userProperties.parallax) {"""
                        assert OLD in s, nn
                        s = s.replace(OLD, NEW, 1)
                    code['script'] = s
        atomic(sp, json.dumps(sc, ensure_ascii=False, indent='\t'))
        # 3) project.json
        pp = os.path.join(proj, 'project.json')
        pr = json.load(open(pp, encoding='utf-8'))
        props = pr['general']['properties']
        props.pop('pupulseona', None)
        props.pop('pupulseonb', None)
        for k, v in (('pupulseax', vals['ax']), ('pupulseay', vals['ay']),
                     ('pupulsebx', vals['bx']), ('pupulseby', vals['by']),
                     ('pupulsesize', vals['r'])):
            props[k]['value'] = v
        props['pupulsecola']['value'] = vals['cola']
        props['pupulsecolb']['value'] = vals['colb']
        props['pupulse']['value'] = True
        atomic(pp, json.dumps(pr, ensure_ascii=False, indent='\t'))
        allvals[nn] = vals
        print('%02d ok A(%.1f,%.1f) B(%.1f,%.1f) r=%.2f' % (nn, vals['ax'], vals['ay'], vals['bx'], vals['by'], vals['r']))
    # 4) config (WE must be stopped)
    for exe in ('wallpaper64.exe', 'wallpaper32.exe', 'wallpaperui.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe], capture_output=True)
    time.sleep(6.5)
    cfg = json.load(open(CFG, encoding='utf-8'))
    mon0 = cfg['25485']['general']['wallpaperconfig']['selectedwallpapers']['Monitor0']
    if 'playlist' in mon0:
        del mon0['playlist']
    wp = cfg['25485']['wproperties']
    for nn, v in allvals.items():
        key = find_proj(nn).replace(os.sep, '/') + '/scene.json'
        mon = wp.setdefault(key, {}).setdefault('Monitor0', {})
        mon.pop('pupulseona', None)
        mon.pop('pupulseonb', None)
        mon.update({'pupulseax': v['ax'], 'pupulseay': v['ay'], 'pupulsebx': v['bx'],
                    'pupulseby': v['by'], 'pupulsesize': v['r'],
                    'pupulsecola': v['cola'], 'pupulsecolb': v['colb'],
                    'pupulse': 'true'})
    atomic(CFG, json.dumps(cfg, ensure_ascii=False, indent='\t'))
    back = json.load(open(CFG, encoding='utf-8'))
    key = find_proj(59).replace(os.sep, '/') + '/scene.json'
    m = back['25485']['wproperties'][key]['Monitor0']
    print('config ok; 59 sample:', m['pupulseax'], m['pupulseay'], m['pupulsecola'])

if __name__ == '__main__':
    main()
