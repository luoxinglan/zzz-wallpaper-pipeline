# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
from scipy import ndimage
import os

BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
d = [x for x in os.listdir(BASE) if x.startswith("zzz_mindscape_05_")][0]
bg2 = np.asarray(Image.open(os.path.join(BASE, d, "materials", "bg2.png")).convert("RGB")).astype(float)
H, W = bg2.shape[:2]
print("bg2", W, "x", H)
mx = bg2.max(axis=2)/255; mn = bg2.min(axis=2)/255
sat = (mx-mn)/np.maximum(mx, 1e-6)
colored = (sat > 0.25) & (mx > 0.15)
lab, n = ndimage.label(colored)
print("total colored comps:", n)
res = []
for k in range(1, n+1):
    sel = lab==k; sz = int(sel.sum())
    if sz < 250: continue
    cy, cx = ndimage.center_of_mass(sel)
    x0,x1,y0,y1 = cx/W*100, cx/W*100, cy/H*100, cy/H*100
    ys, xs = np.where(sel)
    mean = bg2[sel].mean(axis=0).astype(int)
    res.append((sz, round(cx/W*100,2), round(cy/H*100,2),
                round(xs.min()/W*100,1), round(xs.max()/W*100,1),
                round(ys.min()/H*100,1), round(ys.max()/H*100,1), tuple(mean)))
res.sort(key=lambda r: -r[0])
for r in res[:15]:
    print("sz=%6d c=(%s,%s) x[%s..%s] y[%s..%s] rgb=%s" % r)
