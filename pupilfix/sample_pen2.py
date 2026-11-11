# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
import os

CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
BOXES = {
    "06": ("image-454fd2f0c4e1c279965d512a1daa27f3.png", [(17.0,19.0,3.0),(23.35,20.85,3.0)]),
    "08": ("image-aff5e418adffd2feb909798e43a6ab75.png", [(47.8,32.1,3.5)]),
}
for nn, (fn, boxes) in BOXES.items():
    a = np.asarray(Image.open(os.path.join(CACHE, fn)).convert("RGB")).astype(int)
    H, W = a.shape[:2]
    print("== %s" % nn)
    for i,(cx,cy,rad) in enumerate(boxes):
        x0,x1 = max(0,int((cx-rad)/100*W)), min(W,int((cx+rad)/100*W))
        y0,y1 = max(0,int((cy-rad)/100*H)), min(H,int((cy+rad)/100*H))
        b = a[y0:y1, x0:x1]
        mx = b.max(axis=2); mn = b.min(axis=2)
        sat = (mx-mn)/np.maximum(mx,1)
        m = (sat>0.30)&(mx>110)
        px = b[m]
        print("  eye%d box(%d,%d)-(%d,%d) satpx=%d" % (i, x0,y0,x1,y1, len(px)))
        if len(px):
            q = px//24*24
            keys, cnt = np.unique(q.reshape(-1,3), axis=0, return_counts=True)
            order = np.argsort(-cnt)[:10]
            for j in order:
                print("     rgb~(%d,%d,%d) n=%d" % (keys[j][0], keys[j][1], keys[j][2], cnt[j]))
