# -*- coding: utf-8 -*-
"""眼周 ±3% 局部饱和色块质心 = bg2 虹膜实测中心（贴蒙版用）"""
import numpy as np
from PIL import Image
from scipy import ndimage
import os, json

BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
RES = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\results"
JOBS = {"67": 1, "01": 2, "02": 2, "04": 2, "05": 2}
for nn, neye in JOBS.items():
    d = [x for x in os.listdir(BASE) if x.startswith("zzz_mindscape_%s_"%nn)][0]
    bg2 = np.asarray(Image.open(os.path.join(BASE, d, "materials", "bg2.png")).convert("RGB")).astype(float)
    H, W = bg2.shape[:2]
    res = json.load(open(os.path.join(RES, "%d.json"%int(nn)), encoding="utf-8"))
    eyes = [(res["ax"], res["ay"]), (res["bx"], res["by"])] if neye == 2 else [(res["ax"], res["ay"])]
    out = []
    for (ex, ey) in eyes:
        x0, x1 = int((ex-3.5)/100*W), int((ex+3.5)/100*W)
        y0, y1 = int((ey-3.5)/100*H), int((ey+3.5)/100*H)
        b = bg2[max(0,y0):y1, max(0,x0):x1]
        mx = b.max(axis=2)/255; mn = b.min(axis=2)/255
        sat = (mx-mn)/np.maximum(mx,1e-6)
        m = (sat > 0.30) & (mx > 0.20)
        m = ndimage.binary_closing(m, structure=np.ones((5,5)))
        lab, n = ndimage.label(m)
        best = None
        for k in range(1, n+1):
            sel = lab==k; sz = int(sel.sum())
            if sz < 200: continue
            if best is None or sz > best[0]: best = (sz, sel)
        if best:
            sel = best[1]
            cy, cx = ndimage.center_of_mass(sel)
            ix, iy = (x0+cx)/W*100, (y0+cy)/H*100
            mean = b[sel].mean(axis=0).astype(int)
            out.append("eye(%.1f,%.1f)->iris(%.2f,%.2f) sz=%d rgb=%s d=(%+.2f,%+.2f)" % (
                ex, ey, ix, iy, best[0], tuple(mean), ix-ex, iy-ey))
        else:
            out.append("eye(%.1f,%.1f)->NO iris blob" % (ex, ey))
    print(nn, " | ".join(out))
