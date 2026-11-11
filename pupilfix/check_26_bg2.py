# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
import os, glob

BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
d = [x for x in os.listdir(BASE) if x.startswith("zzz_mindscape_26_")][0]
P = os.path.join(BASE, d)
for layer in ("bg1", "bg2", "bg3"):
    img = Image.open(os.path.join(P, "materials", layer + ".png")).convert("RGB")
    W, H = img.size
    a = np.asarray(img)
    x0, x1, y0, y1 = int(0.28*W), int(0.85*W), int(0.08*H), int(0.60*H)
    crop = Image.fromarray(a[y0:y1, x0:x1])
    sc = 1400 / crop.width
    crop = crop.resize((1400, int(crop.height*sc)), Image.LANCZOS)
    crop.save(r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\trace_crops\26_%s_face.png" % layer)
    print(layer, img.size, "crop saved")
