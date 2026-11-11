# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
from scipy import ndimage
import os

CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
AZURE = ((0,140,210),(90,210,255))
LIME  = ((90,170,0),(190,240,110))
RED   = ((180,0,0),(255,110,110))
JOBS = {
    "67": ("image-b572d221420f6a98f399222228cedfa8.png", RED),
    "01": ("image-8e1ea44b1c18e963ebda8193031fb2fc.png", AZURE),
    "02": ("image-b369de3f5133fc76f677b2172b51c517.png", RED),
    "26": ("image-f1e4aa34c279d28145e37afc9544a769.png", AZURE),
    "04": ("image-e5cdd7cf95cb3d6ed365173857513a28.png", AZURE),
    "05": ("image-67c60bd2b8451a08ac5922c410e10445.png", LIME),
}
for nn, (fn, ((r0,g0,b0),(r1,g1,b1))) in JOBS.items():
    a = np.asarray(Image.open(os.path.join(CACHE, fn)).convert("RGB")).astype(int)
    H, W = a.shape[:2]
    R, G, B = a[...,0], a[...,1], a[...,2]
    m = (R>=r0)&(R<=r1)&(G>=g0)&(G<=g1)&(B>=b0)&(B<=b1)
    m = ndimage.binary_closing(m, structure=np.ones((7,7)))
    lab, n = ndimage.label(m)
    comps = []
    for k in range(1, n+1):
        sel = lab==k; s = int(sel.sum())
        if s < 100: continue
        cy, cx = ndimage.center_of_mass(sel)
        ys, xs = np.where(sel)
        comps.append((s, round(cx/W*100,1), round(cy/H*100,1),
                      round(xs.min()/W*100,1), round(xs.max()/W*100,1),
                      round(ys.min()/H*100,1), round(ys.max()/H*100,1)))
    comps.sort(key=lambda c: -c[0])
    print(f"== {nn} n={len(comps)}")
    for c in comps[:10]:
        print(f"   sz={c[0]:5d} c=({c[1]},{c[2]}) x[{c[3]}..{c[4]}] y[{c[5]}..{c[6]}]")

# 26 face zoom 3x
a = np.asarray(Image.open(os.path.join(CACHE, "image-f1e4aa34c279d28145e37afc9544a769.png")).convert("RGB"))
H, W = a.shape[:2]
x0,x1,y0,y1 = int(0.36*W), int(0.60*W), int(0.16*H), int(0.46*H)
crop = Image.fromarray(a[y0:y1, x0:x1])
crop = crop.resize((crop.width*3, crop.height*3), Image.LANCZOS)
crop.save(r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\trace_crops\26_face3x.png")
print("26 face3x saved", (x0,y0,x1,y1))
