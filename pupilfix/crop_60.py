# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
import os
CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
fn = "image-8373cfc14155e107a01447da579468e1.png"
a = np.asarray(Image.open(os.path.join(CACHE, fn)).convert("RGB"))
H, W = a.shape[:2]
x0,x1,y0,y1 = int(0.30*W), int(0.52*W), int(0.20*H), int(0.47*H)
crop = Image.fromarray(a[y0:y1, x0:x1])
crop = crop.resize((crop.width*3, crop.height*3), Image.LANCZOS)
crop.save(r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\trace_crops\60_eyes3x.png")
print("saved crop", (x0,y0,x1,y1))
# 采样虹膜环 vs 笔：紧框采样
b = a[int(0.26*H):int(0.31*H), int(0.43*W):int(0.49*W)].astype(int)
mx = b.max(axis=2); mn = b.min(axis=2)
sat = (mx-mn)/np.maximum(mx,1)
px = b[(sat>0.35)&(mx>120)]
q = px//24*24
keys, cnt = np.unique(q.reshape(-1,3), axis=0, return_counts=True)
order = np.argsort(-cnt)[:8]
print("right-eye box top colors:")
for i in order: print("   (%d,%d,%d) x%d" % (keys[i][0],keys[i][1],keys[i][2],cnt[i]))
