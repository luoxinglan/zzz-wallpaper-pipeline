# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
from scipy import ndimage
import os

CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
IMGS = {
    "67_qingyi":  "image-b572d221420f6a98f399222228cedfa8.png",
    "01_no11":    "image-8e1ea44b1c18e963ebda8193031fb2fc.png",
    "02_seed":    "image-b369de3f5133fc76f677b2172b51c517.png",
    "26_trigger": "image-f1e4aa34c279d28145e37afc9544a769.png",
    "04_yixuan":  "image-e5cdd7cf95cb3d6ed365173857513a28.png",
    "05_idhara":  "image-67c60bd2b8451a08ac5922c410e10445.png",
}
PALETTES = {
    "cyan":    ((0,150,180),(120,225,255)),
    "lime":    ((90,170,0),(190,240,110)),
    "red":     ((180,0,0),(255,110,110)),
    "blue":    ((0,60,200),(130,160,255)),
    "yellow":  ((210,190,0),(255,255,140)),
    "purple":  ((110,50,170),(205,140,255)),
    "orange":  ((235,120,0),(255,195,90)),
    "magenta": ((215,40,140),(255,140,215)),
    "green":   ((0,160,60),(110,235,140)),
}
for tag, fn in IMGS.items():
    p = os.path.join(CACHE, fn)
    shot = np.asarray(Image.open(p).convert("RGB")).astype(int)
    H, W = shot.shape[:2]
    print(f"== {tag} {fn} {W}x{H}")
    R, G, B = shot[...,0], shot[...,1], shot[...,2]
    for name, ((r0,g0,b0),(r1,g1,b1)) in PALETTES.items():
        m = (R>=r0)&(R<=r1)&(G>=g0)&(G<=g1)&(B>=b0)&(B<=b1)
        m = ndimage.binary_closing(m, structure=np.ones((7,7)))
        lab, n = ndimage.label(m)
        comps = []
        for k in range(1, n+1):
            sel = lab==k; s = int(sel.sum())
            if 400 <= s <= 60000:
                cy, cx = ndimage.center_of_mass(sel)
                comps.append((s, round(cx/W*100,1), round(cy/H*100,1)))
        if comps:
            comps.sort(key=lambda c:-c[0])
            tot = sum(c[0] for c in comps)
            print(f"  {name:8s} n={len(comps):3d} tot={tot:7d} top={comps[:5]}")
