# -*- coding: utf-8 -*-
"""v35: per-eye switches + narrow sliders + iris cluster snap + overlay sims for vision verify.

Per project:
  frag v3 (adds g_EnA/g_EnB switch uniforms)
  scene: frozen values snapped to detected iris clusters; 眼A开关/眼B开关 bound
  project.json: switch sliders, narrow position-slider ranges (v±5), size range (v±1.5)
  sim_<NN>.png: additive glow render at final values for vision verification
Config NOT touched here (separate step with WE stopped).
"""
import os, sys, json, math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
SIM = os.path.join(HERE, "sims")
os.makedirs(SIM, exist_ok=True)
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"

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
uniform float g_EnA; // {"material":"眼A开关","default":1.0,"range":[0,1]}
uniform float g_EnB; // {"material":"眼B开关","default":1.0,"range":[0,1]}

void main() {
	vec4 sample4 = texSample2D(g_Texture0, v_TexCoord.xy);

	vec2 quad = vec2(4128.0, 2269.0);
	float r = g_Radius * 0.01 * quad.y;
	vec2 pa = (v_TexCoord.xy - vec2(g_EyeAx, g_EyeAy) * 0.01) * quad;
	vec2 pb = (v_TexCoord.xy - vec2(g_EyeBx, g_EyeBy) * 0.01) * quad;
	float e = r * clamp(g_Soft, 0.02, 1.0);
	float ma = 1.0 - smoothstep(r - e, r, length(pa));
	float mb = 1.0 - smoothstep(r - e, r, length(pb));

	vec3 glow = g_TintA * (v_Pulse * ma * g_EnA) + g_TintB * (v_Pulse * mb * g_EnB);
	gl_FragColor = vec4(min(sample4.rgb + glow, vec3(1.0, 1.0, 1.0)), sample4.a);
}
'''

def find_proj(nn):
    pref = "zzz_mindscape_%02d_" % nn
    for d in os.listdir(BASE):
        if d.startswith(pref):
            return os.path.join(BASE, d)

def hex2f(hx):
    hx = hx.lstrip('#')
    return tuple(int(hx[i:i+2], 16)/255.0 for i in (0, 2, 4))

def atomic(path, data):
    tmp = path + ".tmp"
    open(tmp, "w", encoding="utf-8").write(data)
    os.replace(tmp, path)

def dumpj(o):
    return json.dumps(o, ensure_ascii=False, indent="\t")

def rgb2hex(c):
    return "#%02X%02X%02X" % tuple(int(round(min(1.0, x)*255)) for x in c)

def snap_iris(img, cx_pct, cy_pct, win_pct=4.0):
    """Color-adaptive iris cluster snap. Returns dict or None."""
    H, W = img.shape[:2]
    cx, cy = cx_pct/100*W, cy_pct/100*H
    half = win_pct/100*W
    x0, x1 = int(max(0, cx-half)), int(min(W, cx+half))
    y0, y1 = int(max(0, cy-half)), int(min(H, cy+half))
    if x1-x0 < 40 or y1-y0 < 40:
        return None
    win = img[y0:y1, x0:x1]
    mx = win.max(2); mn = win.min(2)
    sat = np.where(mx > 1e-6, (mx-mn)/np.maximum(mx, 1e-6), 0)
    ccx, ccy = cx-x0, cy-y0
    seed_r = max(6.0, half*0.22)
    yy, xx = np.mgrid[0:win.shape[0], 0:win.shape[1]]
    seed_m = ((xx-ccx)**2+(yy-ccy)**2) <= seed_r*seed_r
    colorful = seed_m & (sat > 0.25) & (mx > 0.10)
    if colorful.sum() >= 25:
        seed = np.median(win[colorful], 0)
        sm, ss = seed.max(), seed.max()-seed.min()
        mask = (sat > 0.22) & (mx > 0.10)
        if ss > 0.15:  # hue-ish similarity on the dominant channel pattern
            d = np.abs(win - seed.reshape(1, 1, 3)).mean(2)
            mask &= d < 0.30
        else:
            mask &= mx < seed.max()+0.15
    else:
        dark = seed_m & (mx < 0.40)
        if dark.sum() >= 25:
            v = np.median(mx[dark])
            mask = mx < v+0.18
        else:
            return None
    mask = ndimage.binary_opening(mask, np.ones((3, 3)))
    lab, n = ndimage.label(mask)
    if not n:
        return None
    li = lab[int(np.clip(ccy, 0, win.shape[0]-1)), int(np.clip(ccx, 0, win.shape[1]-1))]
    if li == 0:  # center not in a component: take nearest component
        best = None
        for i in range(1, n+1):
            m2 = lab == i
            if m2.sum() < 60: continue
            cy2, cx2 = ndimage.center_of_mass(m2)
            dist = math.hypot(cx2-ccx, cy2-ccy)
            if best is None or dist < best[0]:
                best = (dist, m2)
        if best is None or best[0] > half*0.6:
            return None
        m2 = best[1]
    else:
        m2 = lab == li
    if m2.sum() < 60:
        return None
    m2 = ndimage.binary_fill_holes(m2)
    cy2, cx2 = ndimage.center_of_mass(m2)
    ys, xs = np.where(m2)
    w_px = xs.max()-xs.min()+1
    gx, gy = (cx2+x0)/W*100, (cy2+y0)/H*100
    if math.hypot(gx-cx_pct, gy-cy_pct) > win_pct*0.8:
        return None
    vals = mx[m2]
    bright = win[m2][vals >= np.percentile(vals, 55)]
    mean_col = bright.mean(0) if len(bright) else win[m2].mean(0)
    r_pct = w_px/2.0/H*100*0.92
    return {"x": round(gx, 2), "y": round(gy, 2), "r": round(min(5.5, max(0.6, r_pct)), 2),
            "hex": rgb2hex(mean_col), "area": int(m2.sum())}

def make_sim(img, vals, fn):
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    out = img.astype(float)/255.0
    r = vals["r"]/100.0*H
    e = r*0.5
    pulse = 0.75
    for (ex, ey, tint, en) in ((vals["ax"], vals["ay"], vals["cola"], vals["ona"]),
                               (vals["bx"], vals["by"], vals["colb"], vals["onb"])):
        if not en: continue
        t = np.array(hex2f(tint))
        d = np.sqrt((xx-ex/100*W)**2 + (yy-ey/100*H)**2)
        m = (1.0 - np.clip((d-(r-e))/(2*e+1e-6), 0, 1))*pulse
        out = np.minimum(out + t[None, None, :]*m[:, :, None], 1.0)
    im = Image.fromarray((out*255).astype('uint8'))
    # crop around eyes
    mx = (vals["ax"]+vals["bx"])/2; my = (vals["ay"]+vals["by"])/2
    xh = min(20.0, max(10.0, abs(vals["ax"]-vals["bx"])/2+7.0))
    yh = min(14.0, max(8.0, abs(vals["ay"]-vals["by"])/2+6.0))
    x0 = max(0, (mx-xh)/100*W); x1 = min(W, (mx+xh)/100*W)
    y0 = max(0, (my-yh)/100*H); y1 = min(H, (my+yh)/100*H)
    im = im.crop((round(x0), round(y0), round(x1), round(y1)))
    if im.width > 1000:
        im = im.resize((1000, round(im.height*1000/im.width)))
    im.save(fn)

def main(only=None):
    report = []
    for f in sorted(os.listdir(RES)):
        if not f.endswith(".json"): continue
        nn = int(f[:-5])
        if only and nn not in only: continue
        res = json.load(open(os.path.join(RES, f), encoding="utf-8"))
        single = res["color_b"].upper() == "#000000"
        img = np.asarray(Image.open(os.path.join(find_proj(nn), "materials", "bg3.png")).convert("RGB"), dtype=float)
        # snap A
        chg = []
        sA = snap_iris(img, res["ax"], res["ay"])
        if sA:
            if abs(sA["x"]-res["ax"]) > 0.05 or abs(sA["y"]-res["ay"]) > 0.05:
                chg.append("A(%.1f,%.1f)->(%.1f,%.1f)" % (res["ax"], res["ay"], sA["x"], sA["y"]))
            res["ax"], res["ay"] = sA["x"], sA["y"]
            res["r_pct"] = round((res["r_pct"]+sA["r"])/2, 2)
            res["color_a"] = sA["hex"]
        else:
            chg.append("A:no-snap")
        # snap B
        if not single:
            sB = snap_iris(img, res["bx"], res["by"])
            if sB:
                if abs(sB["x"]-res["bx"]) > 0.05 or abs(sB["y"]-res["by"]) > 0.05:
                    chg.append("B(%.1f,%.1f)->(%.1f,%.1f)" % (res["bx"], res["by"], sB["x"], sB["y"]))
                res["bx"], res["by"] = sB["x"], sB["y"]
                res["color_b"] = sB["hex"]
            else:
                chg.append("B:no-snap")
        vals = {"ax": res["ax"], "ay": res["ay"], "bx": res["bx"], "by": res["by"],
                "r": res["r_pct"], "cola": res["color_a"],
                "colb": res["color_a"] if single else res["color_b"],
                "ona": True, "onb": (not single)}
        # frag v3
        proj = find_proj(nn)
        atomic(os.path.join(proj, "shaders", "effects", "pupils.frag"), FRAG)
        # scene
        sp = os.path.join(proj, "scene.json")
        sc = json.load(open(sp, encoding="utf-8"))
        for o in sc.get("objects", []):
            for e in (o.get("effects") or []):
                if e.get("name") == "pupils":
                    csv = e["passes"][0]["constantshadervalues"]
                    csv["眼A水平(%)"]["value"] = vals["ax"]; csv["眼A垂直(%)"]["value"] = vals["ay"]
                    csv["眼B水平(%)"]["value"] = vals["bx"]; csv["眼B垂直(%)"]["value"] = vals["by"]
                    csv["瞳孔半径(层高%)"]["value"] = vals["r"]
                    csv["脉动颜色A"]["value"] = fmt_c(hex2f(vals["cola"]))
                    csv["脉动颜色B"]["value"] = fmt_c(hex2f(vals["colb"]))
                    csv["眼A开关"] = {"user": "pupulseona", "value": True}
                    csv["眼B开关"] = {"user": "pupulseonb", "value": bool(vals["onb"])}
        atomic(sp, dumpj(sc))
        # project.json
        pp = os.path.join(proj, "project.json")
        pr = json.load(open(pp, encoding="utf-8"))
        props = pr["general"]["properties"]
        for k, v in (("pupulseax", vals["ax"]), ("pupulseay", vals["ay"]),
                     ("pupulsebx", vals["bx"]), ("pupulseby", vals["by"])):
            props[k]["value"] = v
            props[k]["min"] = round(max(0, v-5), 2)
            props[k]["max"] = round(min(100, v+5), 2)
            props[k]["step"] = 0.05
        props["pupulsesize"]["value"] = vals["r"]
        props["pupulsesize"]["min"] = round(max(0.2, vals["r"]-1.5), 2)
        props["pupulsesize"]["max"] = round(vals["r"]+1.5, 2)
        props["pupulsesize"]["step"] = 0.02
        props["pupulsecola"]["value"] = fmt_c(hex2f(vals["cola"]))
        props["pupulsecolb"]["value"] = fmt_c(hex2f(vals["colb"]))
        props["pupulseona"] = {"condition": "pupulse.value==true", "index": 16, "order": 116.2,
                               "text": "眼A开关(1开0关)", "type": "slider", "min": 0, "max": 1,
                               "step": 1, "precision": 0, "value": 1}
        props["pupulseonb"] = {"condition": "pupulse.value==true", "index": 16, "order": 116.4,
                               "text": "眼B开关(1开0关)", "type": "slider", "min": 0, "max": 1,
                               "step": 1, "precision": 0, "value": 1 if vals["onb"] else 0}
        atomic(pp, dumpj(pr))
        # sim
        make_sim(img, vals, os.path.join(SIM, "sim_%02d.png" % nn))
        json.dump(res, open(os.path.join(RES, f), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        report.append((nn, "; ".join(chg) if chg else "clean"))
        print("%02d: %s" % (nn, report[-1][1]))
    return report

def fmt_c(rgb):
    return "%.5f %.5f %.5f" % rgb

if __name__ == "__main__":
    only = None
    if len(sys.argv) > 1:
        only = set(int(x) for x in sys.argv[1].split(","))
    main(only)
