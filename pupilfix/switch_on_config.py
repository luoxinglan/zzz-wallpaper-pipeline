# -*- coding: utf-8 -*-
import subprocess, time, json, os
for exe in ('wallpaper64.exe', 'wallpaper32.exe', 'wallpaperui.exe'):
    subprocess.run(['taskkill', '/F', '/IM', exe], capture_output=True)
time.sleep(6.5)
CFG = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\config.json"
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
cfg = json.load(open(CFG, encoding='utf-8'))
mon0 = cfg['25485']['general']['wallpaperconfig']['selectedwallpapers']['Monitor0']
if 'playlist' in mon0:
    del mon0['playlist']
wp = cfg['25485']['wproperties']
n = 0
for d in os.listdir(BASE):
    if not d.startswith('zzz_mindscape_'):
        continue
    key = os.path.join(BASE, d).replace(os.sep, '/') + '/scene.json'
    mon = wp.setdefault(key, {}).setdefault('Monitor0', {})
    mon['pupulseona'] = 1
    mon['pupulseonb'] = 1
    mon['pupulse'] = 'true'
    n += 1
json.dump(cfg, open(CFG, 'w', encoding='utf-8'), ensure_ascii=False, indent='\t')
back = json.load(open(CFG, encoding='utf-8'))
key = os.path.join(BASE, 'zzz_mindscape_01_「11号」').replace(os.sep, '/') + '/scene.json'
m = back['25485']['wproperties'][key]['Monitor0']
print("config switches ON for", n, "| sample 01:", m.get('pupulseona'), m.get('pupulseonb'), m.get('pupulse'))
