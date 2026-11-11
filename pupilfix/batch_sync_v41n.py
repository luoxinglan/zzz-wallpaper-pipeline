# -*- coding: utf-8 -*-
"""v41n 批量三处同步：杀WE -> 写5项目 config+默认值 -> 重启 -> 校验"""
import json, os, sys, time, subprocess
sys.path.insert(0, r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix")
from bake_trace import dirs_of, RES

CFGP = "E:/Program Files (x86)/Steam/steamapps/common/wallpaper_engine/config.json"
WEROOT = "E:/Program Files (x86)/Steam/steamapps/common/wallpaper_engine"
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
NNS = ["50"]

for exe in ("wallpaper64.exe", "wallpaper32.exe", "wallpaperui.exe"):
    subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True)
time.sleep(6.5)

cfg = json.load(open(CFGP, encoding="utf-8"))
for nn in NNS:
    r = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
    P = os.path.join(BASE, dirs_of(nn))
    vals = {"pupulseax": r["ax"], "pupulseay": r["ay"], "pupulsebx": r["bx"], "pupulseby": r["by"]}
    key = P.replace(os.sep, "/") + "/scene.json"
    cfg["25485"]["wproperties"].setdefault(key, {}).setdefault("Monitor0", {}).update(vals)
    pp = os.path.join(P, "project.json")
    pj = json.load(open(pp, encoding="utf-8"))
    for k, v in vals.items():
        if k in pj["general"]["properties"]:
            pj["general"]["properties"][k]["value"] = v
    tmp = pp + ".tmp"
    json.dump(pj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent="\t")
    os.replace(tmp, pp)
    print(nn, "defaults:", {k: pj["general"]["properties"][k]["value"] for k in vals if k in pj["general"]["properties"]})
tmp = CFGP + ".tmp"
json.dump(cfg, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent="\t")
os.replace(tmp, CFGP)
print("config written")

subprocess.Popen([os.path.join(WEROOT, "wallpaper32.exe")], cwd=WEROOT)
time.sleep(14)

# 校验：config 回读 + 渲染进程
cfg2 = json.load(open(CFGP, encoding="utf-8"))
for nn in NNS:
    r = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
    key = os.path.join(BASE, dirs_of(nn)).replace(os.sep, "/") + "/scene.json"
    got = cfg2["25485"]["wproperties"][key]["Monitor0"]
    ok = abs(got["pupulseax"]-r["ax"]) < 0.01 and abs(got["pupulseby"]-r["by"]) < 0.01
    print(nn, "config verify:", "OK" if ok else "MISMATCH %s" % got)
out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq wallpaper32.exe"], capture_output=True, text=True)
print(out.stdout.strip().splitlines()[-1] if len(out.stdout.strip().splitlines()) > 3 else "wallpaper32 NOT RUNNING")
