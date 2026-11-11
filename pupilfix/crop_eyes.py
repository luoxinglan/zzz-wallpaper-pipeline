# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
import os

CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
OUT = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\trace_crops"
os.makedirs(OUT, exist_ok=True)
IMGS = {
    "67": ("image-b572d221420f6a98f399222228cedfa8.png", (56, 48), 26),
    "01": ("image-8e1ea44b1c18e963ebda8193031fb2fc.png", (48, 30), 28),
    "02": ("image-b369de3f5133fc76f677b2172b51c517.png", (68, 27), 26),
    "26": ("image-f1e4aa34c279d28145e37afc9544a769.png", (48, 42), 28),
    "04": ("image-e5cdd7cf95cb3d6ed365173857513a28.png", (26, 36), 30),
    "05": ("image-67c60bd2b8451a08ac5922c410e10445.png", (75, 29), 26),
}
for nn, (fn, (cx, cy), rad) in IMGS.items():
    shot = Image.open(os.path.join(CACHE, fn)).convert("RGB")
    W, H = shot.size
    x0, x1 = max(0, (cx-rad)*W//100), min(W, (cx+rad)*W//100)
    y0, y1 = max(0, (cy-rad)*H//100), min(H, (cy+rad)*H//100)
    crop = shot.crop((x0, x1 and x1 or x1, y0, y1)) if False else shot.crop((x0, y0, x1, y1))
    crop = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
    crop.save(os.path.join(OUT, f"{nn}_eyes.png"))
    a = np.asarray(shot).astype(int)[y0:y1, x0:x1]
    R, G, B = a[...,0], a[...,1], a[...,2]
    mx = a.max(axis=2); mn = a.min(axis=2)
    sat = (mx-mn)/np.maximum(mx,1)
    m = (sat > 0.45) & (mx > 120)
    px = a[m]
    if len(px):
        q = (px//32*32)
        keys, cnt = np.unique(q.reshape(-1,3), axis=0, return_counts=True)
        order = np.argsort(-cnt)[:10]
        print(f"== {nn} crop=({x0},{y0})-({x1},{y1}) sat_px={len(px)}")
        for i in order:
            r,g,b = keys[i]
            print(f"   rgb~({r},{g},{b}) n={cnt[i]}")
    else:
        print(f"== {nn} crop no saturated px")
