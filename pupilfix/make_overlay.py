# -*- coding: utf-8 -*-
"""v37: dedicated top-layer pupil glow overlay (additive), replacing per-layer pupils."""
import json, os, copy
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"

MODEL = '{"autosize": false, "material": "materials/pupilglow.json"}'
MAT = '''{
	"passes": [
		{
			"alphawriting": "default",
			"blending": "additive",
			"cullmode": "nocull",
			"depthtest": "disabled",
			"depthwrite": "disabled",
			"shader": "genericimage4",
			"textures": [
				"pupilbase"
			]
		}
	]
}'''
EFFMAT = '''{
	"passes": [
		{
			"alphawriting": "default",
			"blending": "additive",
			"cullmode": "nocull",
			"depthtest": "disabled",
			"depthwrite": "disabled",
			"shader": "effects/pupils"
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
	"passes" :
	[
		{
			"material" : "materials/effects/pupilsoverlay.json"
		}
	],
	"dependencies" :
	[
		"materials/effects/pupilsoverlay.json",
		"shaders/effects/pupils.frag",
		"shaders/effects/pupils.vert"
	]
}'''

def atomic(path, data):
    tmp = path + '.tmp'
    open(tmp, 'w', encoding='utf-8').write(data)
    os.replace(tmp, path)

def main():
    n = 0
    for d in sorted(os.listdir(BASE)):
        if not d.startswith('zzz_mindscape_'):
            continue
        p = os.path.join(BASE, d)
        # assets
        if not os.path.exists(os.path.join(p, 'materials', 'pupilbase.png')):
            Image.new('RGB', (4, 4), (0, 0, 0)).save(os.path.join(p, 'materials', 'pupilbase.png'))
        atomic(os.path.join(p, 'models', 'pupilglow.json'), MODEL)
        atomic(os.path.join(p, 'materials', 'pupilglow.json'), MAT)
        os.makedirs(os.path.join(p, 'materials', 'effects'), exist_ok=True)
        atomic(os.path.join(p, 'materials', 'effects', 'pupilsoverlay.json'), EFFMAT)
        os.makedirs(os.path.join(p, 'effects', 'pupilsoverlay'), exist_ok=True)
        atomic(os.path.join(p, 'effects', 'pupilsoverlay', 'effect.json'), EFFECT)
        # scene
        sp = os.path.join(p, 'scene.json')
        sc = json.load(open(sp, encoding='utf-8'))
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
        csv_src = None
        for o in sc['objects']:
            if o.get('name') == 'bg3':
                for e in (o.get('effects') or []):
                    if e.get('name') == 'pupils':
                        csv_src = e['passes'][0]['constantshadervalues']
        if csv_src is None:
            print(d, 'no pupils csv found, skip'); continue
        inst = {
            'file': 'effects/pupilsoverlay/effect.json',
            'id': nid, 'name': 'pupilsoverlay',
            'passes': [{'id': nid + 1, 'combos': {'AUDIOPROCESSING': 3},
                        'constantshadervalues': copy.deepcopy(csv_src)}],
            'visible': True,
        }
        obj = {
            'disablepropagation': False, 'id': nid + 2,
            'image': 'models/pupilglow.json', 'name': 'pupilglow',
            'origin': '1920.00000 1080.00000 0.00000',
            'parallaxDepth': '0.00000 0.00000',
            'size': '4128.00000 2269.00000',
            'visible': True,
            'effects': [inst],
        }
        # remove pupils from bg1/2/3
        for o in sc['objects']:
            if o.get('name') in ('bg1', 'bg2', 'bg3'):
                o['effects'] = [e for e in (o.get('effects') or []) if e.get('name') != 'pupils']
        # insert before clock block
        idx = len(sc['objects'])
        for i, o in enumerate(sc['objects']):
            if o.get('name') in ('ClockShadow', 'Clock', 'DateShadow', 'Date', 'weekdayShadow', 'weekday'):
                idx = i
                break
        sc['objects'].insert(idx, obj)
        # JS: overlay follows pupulse master switch
        for o in sc['objects']:
            if o.get('name') == 'scripts':
                code = o.get('visible', {})
                if isinstance(code, dict) and 'script' in code:
                    s = code['script']
                    anchor = 'let all_properties = engine.userProperties;'
                    line = '    try { thisScene.getLayer("pupilglow").visible = !!engine.userProperties["pupulse"]; } catch (e) { }'
                    if anchor in s and 'pupilglow' not in s:
                        code['script'] = s.replace(anchor, anchor + '\n' + line, 1)
        atomic(sp, json.dumps(sc, ensure_ascii=False, indent='\t'))
        n += 1
    print('overlay added:', n)

if __name__ == '__main__':
    main()
