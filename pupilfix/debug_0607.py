# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
from scipy import ndimage
import os, sys, json
sys.path.insert(0, r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix")
from bake_trace import dirs_of, TM, RES

for nn in ("06","07"):
    m = np.asarray(Image.open(os.path.join(TM, "%s_mask.png" % nn))) > 127
    lab, n = ndimage.label(m)
    print("==", nn, "mask blobs:")
    for k in range(1, n+1):
        sel = lab==k; s = int(sel.sum())
        if s < 50: continue
        cy, cx = ndimage.center_of_mass(sel)
        ys, xs = np.where(sel)
        # 实心度：面积/bbox面积
        fill = s / max(1,(xs.max()-xs.min()+1)*(ys.max()-ys.min()+1))
        print("   sz=%6d c=(%.2f,%.2f) bbox x[%d..%d]y[%d..%d] fill=%.2f" % (
            s, cx, cy, xs.min(), xs.max(), ys.min(), ys.max(), fill))
    res = json.load(open(os.path.join(RES, "%d.json"%int(nn)), encoding="utf-8"))
    print("   results now: A(%.2f,%.2f) B(%.2f,%.2f)" % (res["ax"],res["ay"],res["bx"],res["by"]))
