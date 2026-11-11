# -*- coding: utf-8 -*-
"""按 measure_iris 的实测虹膜心微移各眼蒙版 -> 重烘焙 -> apply_v41b"""
import numpy as np
from PIL import Image
from scipy import ndimage
import os, json, sys
sys.path.insert(0, r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix")
from bake_trace import dirs_of, RES, TM, QC

# 实测偏差（dx,dy 图%）：measure_iris.py 输出
D = {
    "67": [(+0.06,+0.48)],
    "01": [(+0.19,+0.13),(-0.23,+0.37)],
    "02": [(+0.55,-0.16),(+0.21,-0.02)],
    "04": [(+0.14,-0.08),(-0.36,+0.66)],
    "05": [(+0.14,-0.75),(+0.82,+0.05)],
}
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
for nn, deltas in D.items():
    d = dirs_of(nn)
    P = os.path.join(BASE, d)
    bg2_img = Image.open(os.path.join(P, "materials", "bg2.png"))
    W2, H2 = bg2_img.size
    mask = np.asarray(Image.open(os.path.join(TM, "%s_mask.png"%nn))) > 127
    lab, n = ndimage.label(mask)
    blobs = []
    for k in range(1, n+1):
        sel = lab==k
        if int(sel.sum()) >= 300: blobs.append(sel)
    blobs.sort(key=lambda s: ndimage.center_of_mass(s)[1])  # 按 x 排序 = A,B
    assert len(blobs) == len(deltas), "%s blobs=%d deltas=%d" % (nn, len(blobs), len(deltas))
    newmask = np.zeros_like(mask)
    for sel, (dx, dy) in zip(blobs, deltas):
        ys, xs = np.where(sel)
        ixs = np.round(xs + dx/100*W2).astype(int)
        iys = np.round(ys + dy/100*H2).astype(int)
        ok = (ixs>=0)&(ixs<W2)&(iys>=0)&(iys<H2)
        newmask[iys[ok], ixs[ok]] = True
    g = ndimage.gaussian_filter(newmask.astype(float), 2.0)
    newmask = g > 0.5
    Image.fromarray((newmask*255).astype(np.uint8)).save(os.path.join(TM, "%s_mask.png"%nn))

    # QC 叠加
    bgv = np.asarray(bg2_img.convert("RGB")).copy()
    bgv[newmask] = (bgv[newmask]*0.35 + np.array([0,255,0])*0.65).astype(np.uint8)
    qim = Image.fromarray(bgv); qim.thumbnail((1500,1500), Image.LANCZOS)
    qim.save(os.path.join(QC, "%s_tracemapped.png"%nn))

    # results = 新质心
    res = json.load(open(os.path.join(RES, "%d.json"%int(nn)), encoding="utf-8"))
    comps2 = []
    lab2, n2 = ndimage.label(newmask)
    for k in range(1, n2+1):
        sel = lab2==k; sz = int(sel.sum())
        if sz >= 300:
            cy, cx = ndimage.center_of_mass(sel)
            comps2.append((round(cx/W2*100,2), round(cy/H2*100,2), sz))
    comps2.sort()
    res["ax"], res["ay"] = comps2[0][0], comps2[0][1]
    if len(comps2) >= 2: res["bx"], res["by"] = comps2[1][0], comps2[1][1]
    else: res["bx"], res["by"] = res["ax"], res["ay"]
    json.dump(res, open(os.path.join(RES, "%d.json"%int(nn)), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(nn, "->", [(b[0], b[1]) for b in comps2])

    # 烘焙 + 回收 + 应用
    bg2f = np.asarray(bg2_img.convert("RGB")).astype(float)/255
    alpha = ndimage.gaussian_filter(newmask.astype(float), 1.8)
    alpha = np.clip(alpha*1.35, 0, 1)
    rgb = np.clip(bg2f*1.35, 0, 1)
    mxch = bg2f.max(axis=2, keepdims=True)
    colnorm = bg2f/np.maximum(mxch, 1e-6)
    rgb = np.maximum(rgb, colnorm*0.45)
    rgba = (np.dstack([rgb*alpha[...,None], alpha[...,None]])*255).astype(np.uint8)
    Image.fromarray(rgba).save(os.path.join(P, "materials", "eyeglow.png"))
    import rebake_v41c as _rb
    _rb._recycle_tex(P)
    import apply_v41b
    print("   apply:", apply_v41b.apply_project(d))
