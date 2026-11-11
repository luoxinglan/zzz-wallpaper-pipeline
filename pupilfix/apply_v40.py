# -*- coding: utf-8 -*-
"""v40: eye-pixel boost effect attached to bg1/2/3 (inherits parallax+mask natively).
Removes v39 standalone eyeflash layer and depth-on-eyeflash (which broke masks)."""
import os, json, copy, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
CFG = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\config.json"

FRAG = r'''varying vec4 v_TexCoord;
varying float v_Pulse;

uniform sampler2D g_Texture0; // {"hidden":true}

uniform float g_GAx; // {"material":"眼A水平(%)"}
uniform float g_GAy; // {"material":"眼A垂直(%)"}
uniform float g_GBx; // {"material":"眼B水平(%)"}
uniform float g_GBy; // {"material":"眼B垂直(%)"}
uniform float g_Gr; // {"material":"瞳孔半径(层高%)"}

void main() {
	vec4 base = texSample2D(g_Texture0, v_TexCoord.xy);
	vec2 pc = v_TexCoord.xy * 100.0;
	float dA = length(vec2((pc.x - g_GAx) * 1.8193, pc.y - g_GAy));
	float dB = length(vec2((pc.x - g_GBx) * 1.8193, pc.y - g_GBy));
	float gate = 1.0 - smoothstep(g_Gr * 0.8, g_Gr * 1.25, min(dA, dB));
	float mx = max(max(base.r, base.g), base.b);
	float mn = min(min(base.r, base.g), base.b);
	float sat = (mx - mn) / max(mx, 0.001);
	float colored = smoothstep(0.14, 0.30, sat) * step(0.05, mx);
	float k = gate * colored;
	vec3 glow = base.rgb * 1.7 * k;
	float lum = max(glow.r, max(glow.g, glow.b));
	gl_FragColor = vec4(glow, clamp(lum * 1.5 + k * 0.10, 0.0, 1.0));
}
'''

EFFMAT = '''{
	"passes": [
		{
			"alphawriting": "default",
			"blending": "normal",
			"cullmode": "nocull",
			"depthtest": "disabled",
			"depthwrite": "disabled",
			"shader": "effects/eyeflash"
		}
	]
}'''

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

def build_csv():
    return {
        "audioamount": {"user": "pupulseamt", "value": 1.0},
        "audiobounds": "0 1",
        "audioexponent": 3.0,
        "frequencymax": 1,
        "frequencymin": 0,
        "眼A水平(%)": {"user": "pupulseax"},
        "眼A垂直(%)": {"user": "pupulseay"},
        "眼B水平(%)": {"user": "pupulsebx"},
        "眼B垂直(%)": {"user": "pupulseby"},
        "瞳孔半径(层高%)": {"user": "pupulsesize"},
        "边缘柔化": {"user": "pupulsesoft", "value": 0.5},
    }

def main():
    stats = []
    for f in sorted(os.listdir(RES)):
        if not f.endswith('.json'):
            continue
        res = json.load(open(os.path.join(RES, f), encoding='utf-8'))
        nn = res['nn']
        proj = find_proj(nn)
        # shader files (vert copied once from pupils.vert)
        vert = open(os.path.join(proj, 'shaders', 'effects', 'pupils.vert'), encoding='utf-8').read()
        atomic(os.path.join(proj, 'shaders', 'effects', 'eyeflash.frag'), FRAG)
        atomic(os.path.join(proj, 'shaders', 'effects', 'eyeflash.vert'), vert)
        atomic(os.path.join(proj, 'materials', 'effects', 'eyeflash.json'), EFFMAT)
        os.makedirs(os.path.join(proj, 'effects', 'eyeflash'), exist_ok=True)
        atomic(os.path.join(proj, 'effects', 'eyeflash', 'effect.json'), EFFECT)
        # scene
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
        csv = build_csv()
        for o in sc['objects']:
            if o.get('name') in ('bg1', 'bg2', 'bg3'):
                effs = [e for e in (o.get('effects') or [])
                        if e.get('name') not in ('pupils', 'pupilsoverlay', 'eyeflash')]
                # insert before first angleband mask instance so glow gets region-masked
                ins = len(effs)
                for i, e in enumerate(effs):
                    if str(e.get('name', '')).startswith('mask'):
                        ins = i
                        break
                inst = {"file": "effects/eyeflash/effect.json", "id": nid, "name": "pupils",
                        "passes": [{"id": nid + 1, "combos": {"AUDIOPROCESSING": 3},
                                    "constantshadervalues": copy.deepcopy(csv)}],
                        "visible": True}
                effs.insert(ins, inst)
                nid += 2
                o['effects'] = effs
            if o.get('name') == 'scripts':
                code = o.get('visible', {})
                if isinstance(code, dict) and 'script' in code:
                    s = code['script']
                    junk = 'try { let efl = thisScene.getLayer("eyeflash");'
                    i = s.find(junk)
                    if i >= 0:
                        j = s.find('} catch (e) { }', i)
                        if j >= 0:
                            s = s[:i] + s[j + len('} catch (e) { }'):]
                            s = s.replace('\n    \n', '\n')
                            code['script'] = s
        atomic(sp, json.dumps(sc, ensure_ascii=False, indent='\t'))
        stats.append(nn)
        print('%02d ok' % nn)
    # config (WE stopped)
    for exe in ('wallpaper64.exe', 'wallpaper32.exe', 'wallpaperui.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe], capture_output=True)
    time.sleep(6.5)
    cfg = json.load(open(CFG, encoding='utf-8'))
    mon0 = cfg['25485']['general']['wallpaperconfig']['selectedwallpapers']['Monitor0']
    if 'playlist' in mon0:
        del mon0['playlist']
    wp = cfg['25485']['wproperties']
    for nn in stats:
        key = find_proj(nn).replace(os.sep, '/') + '/scene.json'
        mon = wp.setdefault(key, {}).setdefault('Monitor0', {})
        mon.pop('pupulseona', None)
        mon.pop('pupulseonb', None)
        mon['pupulse'] = 'true'
    atomic(CFG, json.dumps(cfg, ensure_ascii=False, indent='\t'))
    print('config cleaned for', len(stats))

if __name__ == '__main__':
    main()
