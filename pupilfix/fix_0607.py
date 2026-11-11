# -*- coding: utf-8 -*-
"""06/07 定点修：蒙版=按色相匹配的虹膜本体色块（丢弃方框/眉毛误检）。
06: 紫色系虹膜(colA #8070C0/colB #645C8E)，恒等位±4.5% 窗搜索；
07: 蓝色虹膜环(#686DF0)，PhaseA 位±2.5% 窗，blob-only。"""
import numpy as np
from PIL import Image
from scipy import ndimage
import os, json, sys, colorsys
sys.path.insert(0, r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix")
from bake_trace import dirs_of, RES, TM, QC

BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"

def hue_of(hexcol):
    h = hexcol.lstrip("#")
    r, g, b = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    hs, ls, lv = colorsys.rgb_to_hsv(r, g, b)
    return hs*360, lv

def blob_hue_deg(px):
    mx = px.max(); mn = px.min()
    if mx <= 0: return -999
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    num = 0.5*((r-g)+(r-b)) if False else None
    # 向量化 hue
    import colorsys as _c
    pass

def hue_deg_arr(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=-1); mn = rgb.min(axis=-1)
    d = np.maximum(mx - mn, 1e-9)
    hue = np.zeros(mx.shape)
    m = mx == r
    hue[m] = (60*((g-b)/d) % 360)[m]
    m = mx == g
    hue[m] = (60*((b-r)/d) + 120)[m]
    m = mx == b
    hue[m] = (60*((r-g)/d) + 240)[m]
    return hue

def angdiff(a, b):
    return abs((a-b+180) % 360 - 180)

JOBS = {
    "06": {
        "windows": [(15.9, 16.8, 4.5), (22.1, 20.1, 4.5)],
        "huecols": ["#645C8E", "#8070C0"],
        "hue_tol": 45, "minpx": 300,
    },
    "07": {
        "windows": [(56.14, 36.11, 2.8)],
        "huecols": ["#686DF0"],
        "hue_tol": 40, "minpx": 400,
    },
}
for nn, cfgj in JOBS.items():
    d = dirs_of(nn)
    P = os.path.join(BASE, d)
    bg2_img = Image.open(os.path.join(P, "materials", "bg2.png"))
    W2, H2 = bg2_img.size
    bg2 = np.asarray(bg2_img.convert("RGB")).astype(float)
    mx = bg2.max(axis=2) / 255
    sat = (mx - bg2.min(axis=2) / 255) / np.maximum(mx, 1e-6)
    hues = hue_deg_arr(bg2)
    res = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))

    final = np.zeros((H2, W2), bool)
    print("== %s" % nn)
    for i, (cx, cy, rad) in enumerate(cfgj["windows"]):
        th, _ = hue_of(cfgj["huecols"][i])
        wx0 = max(0, int((cx-rad)/100*W2)); wx1 = min(W2, int((cx+rad)/100*W2))
        wy0 = max(0, int((cy-rad)/100*H2)); wy1 = min(H2, int((cy+rad)/100*H2))
        best = None
        for sthr in (0.30, 0.22, 0.16):
            m = (sat > sthr) & (mx > 0.18)
            m[:wy0, :] = False; m[wy1:, :] = False
            m[:, :wx0] = False; m[:, wx1:] = False
            lab, n = ndimage.label(m)
            for k in range(1, n+1):
                sel = lab == k
                szz = int(sel.sum())
                if szz < cfgj["minpx"]:
                    continue
                hd = hue_deg_arr(bg2[sel])
                dh = np.percentile(np.abs((hd - th + 180) % 360 - 180), 60)
                if dh > cfgj["hue_tol"]:
                    continue
                score = szz * (1 - dh/cfgj["hue_tol"])
                if best is None or score > best[0]:
                    best = (score, sel, szz, dh)
            if best:
                break
        if best is None:
            print("  eye%d NO hue-matched blob!" % i)
            continue
        _, sel, szz, dh = best
        cyx = ndimage.center_of_mass(sel)
        mean = bg2[sel].mean(axis=0).astype(int)
        print("  eye%d blob=%dpx c=(%.2f,%.2f) rgb=%s hue_dh=%.0f" % (
            i, szz, cyx[1]/W2*100, cyx[0]/H2*100, tuple(mean), dh))
        final |= sel

    final = ndimage.binary_closing(final, structure=np.ones((7, 7)))
    final = ndimage.binary_fill_holes(final)
    g = ndimage.gaussian_filter(final.astype(float), 3.0)
    final = g > 0.5
    Image.fromarray((final*255).astype(np.uint8)).save(os.path.join(TM, "%s_mask.png" % nn))
    bgv = np.asarray(bg2_img.convert("RGB")).copy()
    bgv[final] = (bgv[final]*0.35 + np.array([0, 255, 0])*0.65).astype(np.uint8)
    qim = Image.fromarray(bgv)
    qim.thumbnail((1500, 1500), Image.LANCZOS)
    qim.save(os.path.join(QC, "%s_tracemapped.png" % nn))

    comps2 = []
    lab2, n2 = ndimage.label(final)
    for k in range(1, n2+1):
        sel = lab2 == k
        szz = int(sel.sum())
        if szz >= 300:
            cyx = ndimage.center_of_mass(sel)
            comps2.append((round(cyx[1]/W2*100, 2), round(cyx[0]/H2*100, 2), szz))
    comps2.sort()
    print("  blobs:", comps2)
    assert comps2, nn + " empty"
    res["ax"], res["ay"] = comps2[0][0], comps2[0][1]
    if len(comps2) >= 2:
        res["bx"], res["by"] = comps2[1][0], comps2[1][1]
    else:
        res["bx"], res["by"] = res["ax"], res["ay"]
    json.dump(res, open(os.path.join(RES, "%d.json" % int(nn)), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    alpha = ndimage.gaussian_filter(final.astype(float), 1.8)
    alpha = np.clip(alpha*1.35, 0, 1)
    rgb = np.clip(bg2*1.35/255.0, 0, 1)
    mxch = bg2.max(axis=2, keepdims=True)
    colnorm = bg2/np.maximum(mxch, 1e-6)
    rgb = np.maximum(rgb, colnorm*0.45)
    rgba = (np.dstack([rgb*alpha[..., None], alpha[..., None]])*255).astype(np.uint8)
    Image.fromarray(rgba).save(os.path.join(P, "materials", "eyeglow.png"))
    import rebake_v41c as _rb
    _rb._recycle_tex(P)
    import apply_v41b
    print("  apply:", apply_v41b.apply_project(d))
