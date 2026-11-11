# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
from scipy import ndimage
import os, json

BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
RES = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\results"
TM = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\trace_masks"
OUT = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\trace_crops"
for nn in ("50","51","52","54","57","56","63","64","60","06","07","08","13","67","01","02","04","05"):
    d = [x for x in os.listdir(BASE) if x.startswith("zzz_mindscape_%s_"%nn)][0]
    P = os.path.join(BASE, d)
    bg2 = np.asarray(Image.open(os.path.join(P,"materials","bg2.png")).convert("RGB")).copy()
    H, W = bg2.shape[:2]
    mask = np.asarray(Image.open(os.path.join(TM,"%s_mask.png"%nn))) > 127
    res = json.load(open(os.path.join(RES,"%d.json"%int(nn)), encoding="utf-8"))
    lab, n = ndimage.label(mask)
    blobs = []
    for k in range(1, n+1):
        sel = lab==k; sz = int(sel.sum())
        if sz < 300: continue
        cy, cx = ndimage.center_of_mass(sel)
        blobs.append((sz, cx/W*100, cy/H*100))
    blobs.sort()
    print(nn, "blobs:", [("%dpx(%.1f,%.1f)"%b) for b in blobs], "results A(%.1f,%.1f) B(%.1f,%.1f)"%(res["ax"],res["ay"],res["bx"],res["by"]))
    # 拼接每个 blob 的放大图
    tiles = []
    for sz, cx, cy in blobs:
        x0, x1 = int(cx/100*W)-170, int(cx/100*W)+170
        y0, y1 = int(cy/100*H)-120, int(cy/100*H)+120
        x0,y0 = max(0,x0), max(0,y0); x1,y1 = min(W,x1), min(H,y1)
        tile = bg2[y0:y1, x0:x1].copy()
        tm = mask[y0:y1, x0:x1]
        tile[tm] = (tile[tm]*0.35 + np.array([0,255,0])*0.65).astype(np.uint8)
        t = Image.fromarray(tile)
        t = t.resize((t.width*2, t.height*2), Image.LANCZOS)
        tiles.append(t)
    if tiles:
        wsum = sum(t.width for t in tiles) + 20*(len(tiles)-1)
        hmax = max(t.height for t in tiles)
        canvas = Image.new("RGB", (wsum, hmax), (30,30,30))
        ox = 0
        for t in tiles:
            canvas.paste(t, (ox, 0)); ox += t.width + 20
        canvas.save(os.path.join(OUT, "%s_zoomqc.png"%nn))
print("zoom qc saved")
