# -*- coding: utf-8 -*-
"""Apply pupil detection results to all WE zzz_mindscape projects (v2 dual-tint).

Changes per project:
  shaders/effects/pupils.frag  -> additive dual-tint glow (g_TintA/g_TintB)
  scene.json   -> bg2/bg3 pupils instances: eye coords/radius + 脉动颜色A/B entries
  project.json -> pupulseax/ay/bx/by/size defaults, pupulsecola/pupulsecolb (new),
                  remove old pupulsecolor, set pupulse bool
  config.json  -> current values (kill WE first!)

Usage: python pupil_apply.py --dry | --all [--config]
Backups -> backup/<NN>/ and backup/config.json
"""
import os, sys, json, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
BK = os.path.join(HERE, "backup")
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
CFG = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\config.json"

FRAG = r'''varying vec4 v_TexCoord;
varying float v_Pulse;

uniform sampler2D g_Texture0; // {"hidden":true}

uniform float g_EyeAx; // {"material":"眼A水平(%)","default":35.0,"range":[0,100]}
uniform float g_EyeAy; // {"material":"眼A垂直(%)","default":34.0,"range":[0,100]}
uniform float g_EyeBx; // {"material":"眼B水平(%)","default":37.3,"range":[0,100]}
uniform float g_EyeBy; // {"material":"眼B垂直(%)","default":22.7,"range":[0,100]}
uniform float g_Radius; // {"material":"瞳孔半径(层高%)","default":1.6,"range":[0.2,8]}
uniform float g_Soft; // {"material":"边缘柔化","default":0.5,"range":[0,1]}
uniform vec3 g_TintA; // {"material":"脉动颜色A","type":"color","default":"1 1 1"}
uniform vec3 g_TintB; // {"material":"脉动颜色B","type":"color","default":"1 1 1"}

void main() {
	vec4 sample4 = texSample2D(g_Texture0, v_TexCoord.xy);

	vec2 quad = vec2(4128.0, 2269.0);
	float r = g_Radius * 0.01 * quad.y;
	vec2 pa = (v_TexCoord.xy - vec2(g_EyeAx, g_EyeAy) * 0.01) * quad;
	vec2 pb = (v_TexCoord.xy - vec2(g_EyeBx, g_EyeBy) * 0.01) * quad;
	float e = r * clamp(g_Soft, 0.02, 1.0);
	float ma = 1.0 - smoothstep(r - e, r, length(pa));
	float mb = 1.0 - smoothstep(r - e, r, length(pb));

	vec3 glow = g_TintA * (v_Pulse * ma) + g_TintB * (v_Pulse * mb);
	gl_FragColor = vec4(min(sample4.rgb + glow, vec3(1.0, 1.0, 1.0)), sample4.a);
}
'''

SCENE_KEYS = {"眼A水平(%)": "ax", "眼A垂直(%)": "ay", "眼B水平(%)": "bx", "眼B垂直(%)": "by",
              "瞳孔半径(层高%)": "size"}
COLOR_PROP_DEF = {
    "pupulsecola": {"condition": "pupulse.value==true", "index": 17, "order": 117,
                    "text": "瞳孔颜色A", "type": "color", "value": "1 1 1"},
    "pupulsecolb": {"condition": "pupulse.value==true", "index": 17, "order": 117.5,
                    "text": "瞳孔颜色B", "type": "color", "value": "1 1 1"},
}

def find_proj(nn):
    pref = "zzz_mindscape_%02d_" % nn
    for d in os.listdir(BASE):
        if d.startswith(pref):
            return os.path.join(BASE, d)
    raise SystemExit("project %02d not found" % nn)

def hex2f(hx):
    hx = hx.lstrip('#')
    return tuple(int(hx[i:i+2], 16)/255.0 for i in (0, 2, 4))

def fmt_col(rgb):
    return "%.5f %.5f %.5f" % rgb

def atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
    os.replace(tmp, path)

def dumpj(obj):
    return json.dumps(obj, ensure_ascii=False, indent="\t")

def load_result(nn):
    p = os.path.join(RES, "%d.json" % nn)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def backup_once(nn, proj):
    dst = os.path.join(BK, "%02d" % nn)
    if os.path.exists(dst):
        return
    os.makedirs(dst, exist_ok=True)
    for rel in ("scene.json", "project.json", os.path.join("shaders", "effects", "pupils.frag")):
        src = os.path.join(proj, rel)
        d = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(src, d)

def scene_path_key(proj):
    return proj.replace("\\", "/") + "/scene.json"

def apply_project(nn, res, dry):
    proj = find_proj(nn)
    if not dry:
        backup_once(nn, proj)
    vis = res.get("eyes_visible", False)
    vals = {
        "ax": round(float(res["ax"]), 2), "ay": round(float(res["ay"]), 2),
        "bx": round(float(res["bx"]), 2), "by": round(float(res["by"]), 2),
        "size": round(min(8.0, max(0.2, float(res["r_pct"]))), 2),
        "cola": fmt_col(hex2f(res["color_a"])),
        "colb": fmt_col(hex2f(res["color_b"])),
        "enabled": vis,
    }
    fragp = os.path.join(proj, "shaders", "effects", "pupils.frag")
    if open(fragp, encoding="utf-8").read() != FRAG:
        if not dry: atomic(fragp, FRAG)
    # scene.json
    sp = os.path.join(proj, "scene.json")
    sc = json.load(open(sp, encoding="utf-8"))
    n_inst = 0
    for o in sc.get("objects", []):
        for e in (o.get("effects") or []):
            if e.get("name") == "pupils":
                csv = e["passes"][0]["constantshadervalues"]
                for k, fk in SCENE_KEYS.items():
                    if k in csv:
                        csv[k]["value"] = vals[fk]; n_inst += 1
                csv.pop("脉动颜色", None)
                csv["脉动颜色A"] = {"user": "pupulsecola", "value": vals["cola"]}
                csv["脉动颜色B"] = {"user": "pupulsecolb", "value": vals["colb"]}
                n_inst += 2
    if not dry and n_inst:
        atomic(sp, dumpj(sc))
    # project.json
    pp = os.path.join(proj, "project.json")
    pr = json.load(open(pp, encoding="utf-8"))
    props = pr["general"]["properties"]
    for k in ("ax", "ay", "bx", "by", "size"):
        props["pupulse"+k]["value"] = vals[k]
    props.pop("pupulsecolor", None)
    for name, df in COLOR_PROP_DEF.items():
        d = dict(df); d["value"] = vals[name[-4:]]
        props[name] = d
    props["pupulse"]["value"] = vals["enabled"]
    if not dry:
        atomic(pp, dumpj(pr))
    print("%02d %s ax=%.2f ay=%.2f bx=%.2f by=%.2f r=%.2f A=%s B=%s inst=%d" %
          (nn, "ON " if vis else "OFF", vals["ax"], vals["ay"], vals["bx"], vals["by"],
           vals["size"], vals["cola"], vals["colb"], n_inst))
    return vals

def apply_config(allvals, dry):
    if dry:
        print("(dry) config would be updated for %d projects" % len(allvals)); return
    os.makedirs(BK, exist_ok=True)
    cb = os.path.join(BK, "config.json")
    if not os.path.exists(cb):
        shutil.copy2(CFG, cb)
    cfg = json.load(open(CFG, encoding="utf-8"))
    wp = cfg.setdefault("25485", {}).setdefault("wproperties", {})
    for nn, vals in allvals.items():
        key = scene_path_key(find_proj(nn))
        mon = wp.setdefault(key, {}).setdefault("Monitor0", {})
        for k in ("ax", "ay", "bx", "by", "size"):
            mon["pupulse"+k] = vals[k]
        mon.pop("pupulsecolor", None)
        mon["pupulsecola"] = vals["cola"]
        mon["pupulsecolb"] = vals["colb"]
        mon["pupulse"] = vals["enabled"]
    atomic(CFG, dumpj(cfg))
    back = json.load(open(CFG, encoding="utf-8"))
    ok = True
    for nn, vals in allvals.items():
        key = scene_path_key(find_proj(nn))
        mon = back.get("25485", {}).get("wproperties", {}).get(key, {}).get("Monitor0", {})
        if mon.get("pupulsecola") != vals["cola"]:
            ok = False; print("config verify FAIL", nn)
    print("config written, verify:", "OK" if ok else "FAILED")

def main():
    args = sys.argv[1:]
    dry = "--dry" in args
    nns = []
    if "--proj" in args:
        nns = [int(args[args.index("--proj")+1])]
    else:
        nns = sorted(int(f[:-5]) for f in os.listdir(RES) if f.endswith(".json"))
    allvals = {}
    for nn in nns:
        res = load_result(nn)
        if not res:
            print("%02d: no result, skipped" % nn); continue
        if not res.get("eyes_visible"):
            print("%02d: eyes not visible -> stays off" % nn); continue
        allvals[nn] = apply_project(nn, res, dry)
    if "--config" in args:
        apply_config(allvals, dry)

if __name__ == "__main__":
    main()
