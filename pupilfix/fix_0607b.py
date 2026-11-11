# -*- coding: utf-8 -*-
"""06A/07 精修：06A 低阈紫叶并入；07 蓝环收全并 fill 成盘"""
import numpy as np
from PIL import Image
from scipy import ndimage
import os, json, sys
sys.path.insert(0, r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix")
from bake_trace import dirs_of, RES, TM, QC

BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"

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

JOBS = {
    # (中心, 半径%, 目标hue, hue_tol, satthr, valthr, minpx, dilate)
    "06A": ((23.35, 20.95), 2.4, 250, 55, 0.10, 0.25, 100, 5),
    "07":  ((56.6, 34.05), 1.9, 237, 45, 0.14, 0.30, 80, 0),
}
for tag, ((cx, cy), rad, th, htol, sthr, vthr, minpx, dil) in JOBS.items():
    nn = tag[:2]
    d = dirs_of(nn)
    P = os.path.join(BASE, d)
    bg2_img = Image.open(os.path.join(P, "materials", "bg2.png"))
    W2, H2 = bg2_img.size
    bg2 = np.asarray(bg2_img.convert("RGB")).astype(float)
    mx = bg2.max(axis=2) / 255
    sat = (mx - bg2.min(axis=2) / 255) / np.maximum(mx, 1e-6)
    hues = hue_deg_arr(bg2)
    dh = np.abs((hues - th + 180) % 360 - 180)
    m = (sat > sthr) & (mx > vthr) & (dh < htol)
    m = ndimage.binary_closing(m, structure=np.ones((7, 7)))
    lab, n = ndimage.label(m)
    wx0 = max(0, int((cx-rad)/100*W2)); wx1 = min(W2, int((cx+rad)/100*W2))
    wy0 = max(0, int((cy-rad)/100*H2)); wy1 = min(H2, int((cy+rad)/100*H2))
    union = np.zeros((H2, W2), bool)
    for k in range(1, n+1):
        sel = lab == k
        szz = int(sel.sum())
        if szz < minpx:
            continue
        cyx = ndimage.center_of_mass(sel)
        if not (wx0 <= cyx[1] < wx1 and wy0 <= cyx[0] < wy1):
            continue
        union |= sel
        print(tag, "comp", szz, "c=(%.2f,%.2f)" % (cyx[1]/W2*100, cyx[0]/H2*100))
    if dil:
        union = ndimage.binary_dilation(union, iterations=dil)
    union = ndimage.binary_closing(union, structure=np.ones((11, 11)))
    union = ndimage.binary_fill_holes(union)
    g = ndimage.gaussian_filter(union.astype(float), 3.0)
    union = g > 0.5

    # 与现有蒙版融合：目标眼 blob 替换（去掉旧 blob：与 union 相交的旧 blob 删除后并入）
    mask = np.asarray(Image.open(os.path.join(TM, "%s_mask.png" % nn))) > 127
    lab0, n0 = ndimage.label(mask)
    keep = np.zeros_like(mask)
    for k in range(1, n0+1):
        sel = lab0 == k
        if int((sel & union).sum()) > 0.3 * int(sel.sum()):
            continue  # 旧目标眼 blob，删除
        keep |= sel
    final = keep | union
    g = ndimage.gaussian_filter(final.astype(float), 3.0)
    final = g > 0.5
    Image.fromarray((final*255).astype(np.uint8)).save(os.path.join(TM, "%s_mask.png" % nn))
    bgv = np.asarray(bg2_img.convert("RGB")).copy()
    bgv[final] = (bgv[final]*0.35 + np.array([0, 255, 0])*0.65).astype(np.uint8)
    qim = Image.fromarray(bgv)
    qim.thumbnail((1500, 1500), Image.LANCZOS)
    qim.save(os.path.join(QC, "%s_tracemapped.png" % nn))

    res = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
    comps2 = []
    lab2, n2 = ndimage.label(final)
    for k in range(1, n2+1):
        sel = lab2 == k
        szz = int(sel.sum())
        if szz >= 300:
            cyx = ndimage.center_of_mass(sel)
            comps2.append((round(cyx[1]/W2*100, 2), round(cyx[0]/H2*100, 2), szz))
    comps2.sort()
    print(tag, "final blobs:", comps2)
    assert comps2
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
