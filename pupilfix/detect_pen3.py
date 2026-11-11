# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
from scipy import ndimage
import os

CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
JOBS = [
    ("06", "image-454fd2f0c4e1c279965d512a1daa27f3.png", ((210,180,0),(255,230,80)), "yellow"),
    ("08", "image-aff5e418adffd2feb909798e43a6ab75.png", ((0,140,210),(90,210,255)), "azure"),
]
for nn, fn, ((r0,g0,b0),(r1,g1,b1)), name in JOBS:
    a = np.asarray(Image.open(os.path.join(CACHE, fn)).convert("RGB")).astype(int)
    H, W = a.shape[:2]
    R, G, B = a[...,0], a[...,1], a[...,2]
    m = (R>=r0)&(R<=r1)&(G>=g0)&(G<=g1)&(B>=b0)&(B<=b1)
    m = ndimage.binary_closing(m, structure=np.ones((7,7)))
    lab, n = ndimage.label(m)
    comps = []
    for k in range(1, n+1):
        sel = lab==k; s = int(sel.sum())
        if 60 <= s <= 80000:
            cy, cx = ndimage.center_of_mass(sel)
            comps.append((int(s), round(cx/W*100,1), round(cy/H*100,1)))
    comps.sort(key=lambda c:-c[0])
    print("== %s %s n=%d" % (nn, name, len(comps)))
    for c in comps[:12]: print("   sz=%5d c=(%s,%s)" % c)
