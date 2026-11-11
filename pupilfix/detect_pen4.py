# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
from scipy import ndimage
import os, json

CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
RES = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\results"
fn = "image-8373cfc14155e107a01447da579468e1.png"
a = np.asarray(Image.open(os.path.join(CACHE, fn)).convert("RGB")).astype(int)
H, W = a.shape[:2]
print("== 60 vivian", fn, "%dx%d" % (W, H))
res = json.load(open(os.path.join(RES, "60.json"), encoding="utf-8"))
print("results: A(%.2f,%.2f) B(%.2f,%.2f) r=%.2f colA=%s colB=%s" % (
    res["ax"], res["ay"], res["bx"], res["by"], res["r_pct"], res.get("color_a"), res.get("color_b")))
R, G, B = a[...,0], a[...,1], a[...,2]
PALETTES = {
    "cyan":  ((0,150,180),(120,225,255)),
    "lime":  ((90,170,0),(190,240,110)),
    "red":   ((180,0,0),(255,110,110)),
    "blue":  ((0,60,200),(130,160,255)),
    "azure": ((0,140,210),(90,210,255)),
    "gold":  ((210,180,0),(255,230,80)),
    "yellow":((210,190,0),(255,255,140)),
    "pink":  ((230,90,140),(255,170,210)),
    "purple":((110,50,170),(205,140,255)),
    "lav":   ((170,140,220),(225,195,255)),
}
for name, ((r0,g0,b0),(r1,g1,b1)) in PALETTES.items():
    m = (R>=r0)&(R<=r1)&(G>=g0)&(G<=g1)&(B>=b0)&(B<=b1)
    m = ndimage.binary_closing(m, structure=np.ones((7,7)))
    lab, n = ndimage.label(m)
    comps = []
    for k in range(1, n+1):
        sel = lab==k; s = int(sel.sum())
        if 80 <= s <= 80000:
            cy, cx = ndimage.center_of_mass(sel)
            comps.append((int(s), round(cx/W*100,1), round(cy/H*100,1)))
    comps.sort(key=lambda c:-c[0])
    if comps:
        print("  %-7s n=%3d top=%s" % (name, len(comps), comps[:7]))
