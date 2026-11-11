# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
from scipy import ndimage
import os, json

CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
RES = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\results"
IMGS = {
    "06": "image-454fd2f0c4e1c279965d512a1daa27f3.png",
    "07": "image-ee3a9c2eebd3c8eb7f7a4e0425f18547.png",
    "08": "image-aff5e418adffd2feb909798e43a6ab75.png",
    "13": "image-97c012fdec1cc043a126ac97e90ecc96.png",
}
PALETTES = {
    "cyan":  ((0,150,180),(120,225,255)),
    "lime":  ((90,170,0),(190,240,110)),
    "red":   ((180,0,0),(255,110,110)),
    "blue":  ((0,60,200),(130,160,255)),
    "azure": ((0,140,210),(90,210,255)),
    "yellow":((210,190,0),(255,255,140)),
    "pink":  ((230,90,140),(255,170,210)),
    "purple":((110,50,170),(205,140,255)),
}
for nn, fn in IMGS.items():
    a = np.asarray(Image.open(os.path.join(CACHE, fn)).convert("RGB")).astype(int)
    H, W = a.shape[:2]
    print("== %s %s %dx%d" % (nn, fn, W, H))
    res = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
    print("   results: A(%.2f,%.2f) B(%.2f,%.2f) r=%.2f colA=%s colB=%s" % (
        res["ax"], res["ay"], res["bx"], res["by"], res["r_pct"], res.get("color_a"), res.get("color_b")))
    R, G, B = a[...,0], a[...,1], a[...,2]
    for name, ((r0,g0,b0),(r1,g1,b1)) in PALETTES.items():
        m = (R>=r0)&(R<=r1)&(G>=g0)&(G<=g1)&(B>=b0)&(B<=b1)
        m = ndimage.binary_closing(m, structure=np.ones((7,7)))
        lab, n = ndimage.label(m)
        comps = []
        for k in range(1, n+1):
            sel = lab==k; s = int(sel.sum())
            if 100 <= s <= 60000:
                cy, cx = ndimage.center_of_mass(sel)
                comps.append((s, round(cx/W*100,1), round(cy/H*100,1)))
        comps.sort(key=lambda c:-c[0])
        if comps:
            print("   %-7s n=%3d top=%s" % (name, len(comps), comps[:6]))
