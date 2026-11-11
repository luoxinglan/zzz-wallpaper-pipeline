# -*- coding: utf-8 -*-
"""05 伊德海莉专用：NCC 锁错峰，改用旧真值锚定——每团描线质心钉到旧 results 眼心"""
import numpy as np
from PIL import Image
from scipy import ndimage
import os, json, sys
sys.path.insert(0, r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix")
from bake_trace import dirs_of, RES, TM, QC

SHOT = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40\image-67c60bd2b8451a08ac5922c410e10445.png"
LIME = ((90,170,0),(190,240,110))
EYES_SCREEN = [(82.2,29.2),(75.0,26.4)]           # 两团描线质心（屏幕%）
TARGETS_IMG  = [(78.35,29.8),(72.4,28.4)]          # 旧 results 真值眼心（图%）

nn = "05"
shot = np.asarray(Image.open(SHOT).convert("RGB")).astype(int)
H1, W1 = shot.shape[:2]
R,G,B = shot[...,0], shot[...,1], shot[...,2]
trace = (R>=LIME[0][0])&(R<=LIME[1][0])&(G>=LIME[0][1])&(G<=LIME[1][1])&(B>=LIME[0][2])&(B<=LIME[1][2])
trace = ndimage.binary_closing(trace, structure=np.ones((7,7)))
lab, n = ndimage.label(trace)
# 挑出两团描线组件（排除图标区）
comps = []
for k in range(1, n+1):
    sel = lab==k; sz = int(sel.sum())
    if sz < 120: continue
    cy, cx = ndimage.center_of_mass(sel)
    sx, sy = cx/W1*100, cy/H1*100
    if sx < 12 or sy > 95: continue
    for ei,(ex,ey) in enumerate(EYES_SCREEN):
        if abs(sx-ex) < 7 and abs(sy-ey) < 7:
            comps.append((ei, sel, sx, sy, sz)); break
assert len(comps) >= 2, "comps=%d" % len(comps)
print("stroke comps:", [(e[0], e[4], round(e[2],1), round(e[3],1)) for e in comps])

d = dirs_of(nn)
P = os.path.join(r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects", d)
bg2_img = Image.open(os.path.join(P, "materials", "bg2.png"))
W2, H2 = bg2_img.size
sc = H2 / H1

mask = np.zeros((H2, W2), bool)
for ei, sel, sx, sy, sz in comps:
    ys, xs = np.where(sel)
    # 逐眼平移：描线质心(像素差×比例) -> 真值眼心(图%)
    tx, ty = TARGETS_IMG[ei][0]/100*W2, TARGETS_IMG[ei][1]/100*H2
    ixs = np.round((xs - np.mean(xs)) * sc + tx).astype(int)
    iys = np.round((ys - np.mean(ys)) * sc + ty).astype(int)
    ok = (ixs>=0)&(ixs<W2)&(iys>=0)&(iys<H2)
    mask[iys[ok], ixs[ok]] = True

mask = ndimage.binary_closing(mask, structure=np.ones((9,9)))
mask = ndimage.binary_fill_holes(mask)
g = ndimage.gaussian_filter(mask.astype(float), 5.0)
mask = g > 0.5

Image.fromarray((mask*255).astype(np.uint8)).save(os.path.join(TM, "05_mask.png"))
bgv = np.asarray(bg2_img.convert("RGB")).copy()
bgv[mask] = (bgv[mask]*0.35 + np.array([0,255,0])*0.65).astype(np.uint8)
qim = Image.fromarray(bgv); qim.thumbnail((1500,1500), Image.LANCZOS)
qim.save(os.path.join(QC, "05_tracemapped.png"))

# 质心 -> results
res = json.load(open(os.path.join(RES, "5.json"), encoding="utf-8"))
comps2 = []
lab2, n2 = ndimage.label(mask)
for k in range(1, n2+1):
    sel = lab2==k; sz = int(sel.sum())
    if sz >= 300:
        cy, cx = ndimage.center_of_mass(sel)
        comps2.append((cx/W2*100, cy/H2*100, sz))
comps2.sort()
print("mapped blobs:", [("%.2f,%.2f"%b[:2], b[2]) for b in comps2])
assert len(comps2) == 2, "blobs=%d" % len(comps2)
res["ax"], res["ay"] = round(comps2[0][0],2), round(comps2[0][1],2)
res["bx"], res["by"] = round(comps2[1][0],2), round(comps2[1][1],2)
res["notes"] = res.get("notes","") + "; v41n trace锚定旧真值(屏幕描线质心->旧眼心)"
json.dump(res, open(os.path.join(RES, "5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 烘焙（与 bake_trace 相同参数）+ 回收 tex + apply_v41b
bg2f = np.asarray(bg2_img.convert("RGB")).astype(float)/255
alpha = ndimage.gaussian_filter(mask.astype(float), 1.8)
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
msg = apply_v41b.apply_project(d)
print("apply:", msg)
