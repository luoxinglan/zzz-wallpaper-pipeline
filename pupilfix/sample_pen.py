# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
import os

CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
IMGS = {
    "67": ("image-b572d221420f6a98f399222228cedfa8.png", [(55.9,48.0,4)]),
    "01": ("image-8e1ea44b1c18e963ebda8193031fb2fc.png", [(43,32,6),(54,28,6)]),
    "02": ("image-b369de3f5133fc76f677b2172b51c517.png", [(65.2,26.3,5),(70.6,27.3,5)]),
    "04": ("image-e5cdd7cf95cb3d6ed365173857513a28.png", [(21.3,40.4,6),(30.9,32.3,6)]),
    "05": ("image-67c60bd2b8451a08ac5922c410e10445.png", [(78.4,29.8,5),(72.4,28.4,5)]),
}
for nn, (fn, boxes) in IMGS.items():
    a = np.asarray(Image.open(os.path.join(CACHE, fn)).convert("RGB")).astype(int)
    H, W = a.shape[:2]
    print(f"== {nn}")
    for i,(cx,cy,rad) in enumerate(boxes):
        x0,x1 = max(0,int((cx-rad)/100*W)), min(W,int((cx+rad)/100*W))
        y0,y1 = max(0,int((cy-rad)/100*H)), min(H,int((cy+rad)/100*H))
        b = a[y0:y1, x0:x1]
        mx = b.max(axis=2); mn = b.min(axis=2)
        sat = (mx-mn)/np.maximum(mx,1)
        m = (sat>0.35)&(mx>110)
        px = b[m]
        out = f"  eye{i} box({x0},{y0})-({x1},{y1}) satpx={len(px)}"
        if len(px):
            q = px//24*24
            keys, cnt = np.unique(q.reshape(-1,3), axis=0, return_counts=True)
            order = np.argsort(-cnt)[:8]
            tops = " | ".join(f"({keys[i][0]},{keys[i][1]},{keys[i][2]})x{cnt[i]}" for i in order)
            out += "\n     " + tops
        print(out)

# 26 full head crop
fn = "image-f1e4aa34c279d28145e37afc9544a769.png"
a = np.asarray(Image.open(os.path.join(CACHE, fn)).convert("RGB")).astype(int)
H, W = a.shape[:2]
x0,x1,y0,y1 = int(0.25*W), int(0.70*W), int(0.08*H), int(0.72*H)
crop = Image.fromarray(a[y0:y1, x0:x1].astype(np.uint8))
crop = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
crop.save(r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\trace_crops\26_head.png")
print("26 head crop saved", (x0,y0,x1,y1))
