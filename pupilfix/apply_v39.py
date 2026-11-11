# -*- coding: utf-8 -*-
"""v39: baked eye-shape glow layer (eyeflash) + small core fallback circles."""
import json, os, shutil, subprocess, time
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
CFG = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\config.json"

VERT = None  # filled from pupils.vert at runtime (identical for all)
FRAG = r'''varying vec4 v_TexCoord;
varying float v_Pulse;

uniform sampler2D g_Texture0; // {"hidden":true}

void main() {
	vec4 t = texSample2D(g_Texture0, v_TexCoord.xy);
	gl_FragColor = vec4(t.rgb * (v_Pulse * 1.5), t.a);
}
'''
EFFMAT = '''{
	"passes": [
		{
			"alphawriting": "default",
			"blending": "additive",
			"cullmode": "nocull",
			"depthtest": "disabled",
			"depthwrite": "disabled",
			"shader": "effects/eyeflash"
		}
	]
}'''
BASEMAT = '''{
	"passes": [
		{
			"alphawriting": "default",
			"blending": "additive",
			"cullmode": "nocull",
			"depthtest": "disabled",
			"depthwrite": "disabled",
			"shader": "genericimage4",
			"textures": ["eyeglow"]
		}
	]
}'''
MODEL = '{"autosize": false, "material": "materials/eyeflashbase.json"}'
EFFECT = '''{
	"version" : 1,
	"replacementkey" : "pulse",
	"name" : "ui_editor_effect_pulse_title",
	"description" : "ui_editor_effect_pulse_description",
	"group" : "animate",
	"preview" : "preview/project.json",
	"passes" : [ { "material" : "materials/effects/eyeflash.json" } ],
	"dependencies" :
	[
		"materials/effects/eyeflash.json",
		"shaders/effects/eyeflash.frag",
		"shaders/effects/eyeflash.vert"
	]
}'''

def atomic(path, data):
    tmp = path + '.tmp'
    open(tmp, 'w', encoding='utf-8').write(data)
    os.replace(tmp, path)

def find_proj(nn):
    pref = 'zzz_mindscape_%02d_' % nn
    for d in os.listdir(BASE):
        if d.startswith(pref):
            return os.path.join(BASE, d)

def bake_eyeglow(proj, res):
    bg2 = np.asarray(Image.open(os.path.join(proj, 'materials', 'bg2.png')).convert('RGB'), dtype=float) / 255
    H, W = bg2.shape[:2]
    mx = bg2.max(2); mn = bg2.min(2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    colored = (sat > 0.28) & (mx > 0.13)
    yy, xx = np.mgrid[0:H, 0:W]
    def gate(cx, cy, rad):
        return ((xx - cx / 100 * W) ** 2 + (yy - cy / 100 * H) ** 2) <= rad * rad
    rpx = res['r_pct'] / 100 * H
    g = gate(res['ax'], res['ay'], rpx * 1.6)
    if res['color_b'].upper() != '#000000' or (res['bx'], res['by']) != (res['ax'], res['ay']):
        g = g | gate(res['bx'], res['by'], rpx * 1.6)
    mask = colored & g
    mask = ndimage.binary_closing(mask, np.ones((5, 5)))
    if mask.sum() < 40:
        g2 = gate(res['ax'], res['ay'], rpx * 3.2) | gate(res['bx'], res['by'], rpx * 3.2)
        mask = colored & g2
        mask = ndimage.binary_closing(mask, np.ones((5, 5)))
    alpha = ndimage.gaussian_filter(mask.astype(float), 1.6)
    rgb = np.clip(bg2 * 1.35, 0, 1)
    out = np.dstack([rgb, alpha[:, :, None]])
    Image.fromarray((out * 255).astype('uint8'), 'RGBA').save(os.path.join(proj, 'materials', 'eyeglow.png'))
    return int(mask.sum())

def main():
    global VERT
    vert_src = None
    stats = []
    for f in sorted(os.listdir(RES)):
        if not f.endswith('.json'):
            continue
        res = json.load(open(os.path.join(RES, f), encoding='utf-8'))
        nn = res['nn']
        proj = find_proj(nn)
        if VERT is None:
            VERT = open(os.path.join(proj, 'shaders', 'effects', 'pupils.vert'), encoding='utf-8').read()
        # 1) bake
        area = bake_eyeglow(proj, res)
        # 2) files
        atomic(os.path.join(proj, 'models', 'eyeflash.json'), MODEL)
        atomic(os.path.join(proj, 'materials', 'eyeflashbase.json'), BASEMAT)
        atomic(os.path.join(proj, 'materials', 'effects', 'eyeflash.json'), EFFMAT)
        atomic(os.path.join(proj, 'shaders', 'effects', 'eyeflash.frag'), FRAG)
        atomic(os.path.join(proj, 'shaders', 'effects', 'eyeflash.vert'), VERT)
        os.makedirs(os.path.join(proj, 'effects', 'eyeflash'), exist_ok=True)
        atomic(os.path.join(proj, 'effects', 'eyeflash', 'effect.json'), EFFECT)
        # 3) scene
        sp = os.path.join(proj, 'scene.json')
        sc = json.load(open(sp, encoding='utf-8'))
        sc['objects'] = [o for o in sc['objects'] if o.get('name') not in ('pupilglow', 'eyeflash')]
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
        csv = {
            "audioamount": {"user": "pupulseamt", "value": 1.0},
            "audiobounds": "0 1",
            "audioexponent": 3.0,
            "frequencymax": 1,
            "frequencymin": 0,
        }
        inst = {"file": "effects/eyeflash/effect.json", "id": nid, "name": "eyeflash",
                "passes": [{"id": nid + 1, "combos": {"AUDIOPROCESSING": 3},
                            "constantshadervalues": csv}], "visible": True}
        obj = {"disablepropagation": False, "id": nid + 2, "image": "models/eyeflash.json",
               "name": "eyeflash", "origin": "1920.00000 1080.00000 0.00000",
               "parallaxDepth": "0.00000 0.00000", "size": "4128.00000 2269.00000",
               "visible": True, "effects": [inst]}
        # shrink fallback circles + restore audio bounds on bg pupils instances
        rsmall = round(max(0.4, res['r_pct'] * 0.55), 2)
        for o in sc['objects']:
            if o.get('name') in ('bg1', 'bg2', 'bg3'):
                for e in (o.get('effects') or []):
                    if e.get('name') == 'pupils':
                        c = e['passes'][0]['constantshadervalues']
                        c['瞳孔半径(层高%)']['value'] = rsmall
                        c['audiobounds'] = "0 1"
            if o.get('name') == 'scripts':
                code = o.get('visible', {})
                if isinstance(code, dict) and 'script' in code:
                    s = code['script']
                    s = s.replace('thisScene.getLayer("pupilglow")', 'thisScene.getLayer("eyeflash")')
                    code['script'] = s
        idx = len(sc['objects'])
        for i, o in enumerate(sc['objects']):
            if o.get('name') in ('ClockShadow', 'Clock', 'DateShadow', 'Date', 'weekdayShadow', 'weekday'):
                idx = i
                break
        sc['objects'].insert(idx, obj)
        atomic(sp, json.dumps(sc, ensure_ascii=False, indent='\t'))
        # 4) project default size
        pp = os.path.join(proj, 'project.json')
        pr = json.load(open(pp, encoding='utf-8'))
        pr['general']['properties']['pupulsesize']['value'] = rsmall
        atomic(pp, json.dumps(pr, ensure_ascii=False, indent='\t'))
        stats.append((nn, area, rsmall))
        print('%02d baked px=%d fallback r=%.2f' % (nn, area, rsmall))
    # 5) config: size values (WE stopped)
    for exe in ('wallpaper64.exe', 'wallpaper32.exe', 'wallpaperui.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe], capture_output=True)
    time.sleep(6.5)
    cfg = json.load(open(CFG, encoding='utf-8'))
    mon0 = cfg['25485']['general']['wallpaperconfig']['selectedwallpapers']['Monitor0']
    if 'playlist' in mon0:
        del mon0['playlist']
    wp = cfg['25485']['wproperties']
    for nn, area, rsmall in stats:
        key = find_proj(nn).replace(os.sep, '/') + '/scene.json'
        mon = wp.setdefault(key, {}).setdefault('Monitor0', {})
        mon['pupulsesize'] = rsmall
    atomic(CFG, json.dumps(cfg, ensure_ascii=False, indent='\t'))
    print('config sizes written for', len(stats))

if __name__ == '__main__':
    main()
