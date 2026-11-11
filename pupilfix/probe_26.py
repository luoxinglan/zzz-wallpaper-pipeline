# -*- coding: utf-8 -*-
"""零写入探针：26 的蓝笔描线经 NCC 映射到 bg2 后落在哪里"""
import numpy as np
from PIL import Image
from scipy import ndimage
import os, sys
sys.path.insert(0, r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix")
from bake_trace import ncc_match, dirs_of, RES

CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
nn = "26"
shot = np.asarray(Image.open(os.path.join(CACHE, "image-f1e4aa34c279d28145e37afc9544a769.png")).convert("RGB")).astype(int)
H1, W1 = shot.shape[:2]
R, G, B = shot[...,0], shot[...,1], shot[...,2]
AZURE = ((0,140,210),(90,210,255))
trace = (R>=AZURE[0][0])&(R<=AZURE[1][0])&(G>=AZURE[0][1])&(G<=AZURE[1][1])&(B>=AZURE[0][2])&(B<=AZURE[1][2])
trace = ndimage.binary_closing(trace, structure=np.ones((7,7)))
lab, n = ndimage.label(trace)
keep = np.zeros_like(trace)
# 只留眼部区域组件（两个蓝笔迹：大圈(57.2,33.5) + 小勾(42.5,22.6)），排除桌面图标(x<12%)与任务栏(y>95%)
for k in range(1, n+1):
    sel = lab==k; sz = int(sel.sum())
    if sz < 60: continue
    cy, cx = ndimage.center_of_mass(sel)
    scx, scy = cx/W1*100, cy/H1*100
    if scx < 12 or scy > 95: continue
    if not (abs(scx-57.2)<8 and abs(scy-33.5)<8) and not (abs(scx-42.5)<8 and abs(scy-22.6)<8): continue
    keep |= sel
    print("kept comp sz=%d at (%.1f,%.1f)" % (sz, scx, scy))

trace = ndimage.binary_closing(keep, iterations=12)
trace = ndimage.binary_fill_holes(trace)
trace = ndimage.binary_dilation(trace, iterations=3)

ys, xs = np.where(keep)
bx0, bx1 = xs.min(), xs.max(); by0, by1 = ys.min(), ys.max()
mx, my = (bx0+bx1)//2, (by0+by1)//2
ext = min(220, max(bx1-bx0, by1-by0) * 0.8 + 120)
tx0, tx1 = max(0, int(mx-ext)), min(W1, int(mx+ext))
ty0, ty1 = max(0, int(my-ext)), min(H1, int(my+ext))
tmpl_rgb = shot[ty0:ty1, tx0:tx1].astype(float)
tr = keep[ty0:ty1, tx0:tx1]
med = ndimage.median_filter(tmpl_rgb, size=(9,9,1))
tmpl_rgb[tr] = med[tr]
tmpl = tmpl_rgb.mean(axis=2)
ch, cw = tmpl.shape

P = os.path.join(r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects", dirs_of(nn))
bg2_img = Image.open(os.path.join(P, "materials", "bg2.png"))
W2, H2 = bg2_img.size
sx_scale = H2/H1 * (W2/H2) / (W2/H2)  # = H2/H1? bake_trace: sx_scale = W2/(H1*W2/H2) = H2/H1
sx_scale = H2/H1
sy_scale = H2/H1
tmpl_img = np.asarray(Image.fromarray(tmpl.astype(np.uint8)).resize((int(cw*sx_scale), int(ch*sy_scale)), Image.LANCZOS)).astype(float)
bg2 = np.asarray(bg2_img.convert("L")).astype(float)
res0 = __import__("json").load(open(os.path.join(RES, "26.json"), encoding="utf-8"))
ex, ey = int((res0["ax"]+res0["bx"])/2/100*W2), int((res0["ay"]+res0["by"])/2/100*H2)
rx, ry = int(0.18*W2), int(0.19*H2)
x0, x1 = max(0, ex-rx), min(W2, ex+rx)
y0, y1 = max(0, ey-ry), min(H2, ey+ry)
ncc, yy, xx = ncc_match(bg2[y0:y1, x0:x1], tmpl_img)
off_x = (x0+xx) - tx0*sx_scale
off_y = (y0+yy) - ty0*sy_scale
print("ncc=%.3f offset=(%.0f,%.0f)" % (ncc, off_x, off_y))

mask = np.zeros((H2, W2), bool)
ys, xs = np.where(trace)
ixs = (xs*sx_scale + off_x).astype(int)
iys = (ys*sy_scale + off_y).astype(int)
ok = (ixs>=0)&(ixs<W2)&(iys>=0)&(iys<H2)
mask[iys[ok], ixs[ok]] = True
mask = ndimage.binary_closing(mask, structure=np.ones((9,9)))
mask = ndimage.binary_fill_holes(mask)
lab2, n2 = ndimage.label(mask)
for k in range(1, n2+1):
    sel = lab2==k; sz = int(sel.sum())
    if sz < 300: continue
    cy, cx = ndimage.center_of_mass(sel)
    ys2, xs2 = np.where(sel)
    print("mapped comp sz=%d center=(%.2f,%.2f)%% x[%.1f..%.1f] y[%.1f..%.1f]" % (
        sz, cx/W2*100, cy/H2*100, xs2.min()/W2*100, xs2.max()/W2*100, ys2.min()/H2*100, ys2.max()/H2*100))

bgv = np.asarray(bg2_img.convert("RGB")).copy()
bgv[mask] = (bgv[mask]*0.35 + np.array([0,255,0])*0.65).astype(np.uint8)
qim = Image.fromarray(bgv)
ys2, xs2 = np.where(mask)
if len(xs2):
    cx0, cx1 = max(0,xs2.min()-200), min(W2,xs2.max()+200)
    cy0, cy1 = max(0,ys2.min()-200), min(H2,ys2.max()+200)
    qim = qim.crop((cx0,cy0,cx1,cy1))
qim.thumbnail((1400,1400), Image.LANCZOS)
qim.save(r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\trace_crops\26_probe_overlay.png")

# bg2 单眼区域高倍放大（窄眼缝在 results(52.1,38.7) 附近）
a = np.asarray(bg2_img.convert("RGB"))
ex0, ey0 = int(0.52*W2), int(0.42*H2)
c = Image.fromarray(a[ey0-int(0.06*H2):ey0+int(0.06*H2), ex0-int(0.09*W2):ex0+int(0.09*W2)])
c = c.resize((c.width*2, c.height*2), Image.LANCZOS)
c.save(r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\trace_crops\26_bg2_eyezoom.png")
print("probe done")
