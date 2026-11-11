# -*- coding: utf-8 -*-
"""Contact sheet: all 60 projects' bg3 thumbnails (with NN+name labels) for visual matching."""
import os, sys
from PIL import Image, ImageDraw

ROOT = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
OUT = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\contact_bg3.png"
TW, TH, COLS = 320, 180, 6

projs = sorted(os.listdir(ROOT))
cells = []
for p in projs:
    if not p.startswith("zzz_mindscape_"):
        continue
    nn = p.split("_")[2]
    bg3 = os.path.join(ROOT, p, "materials", "bg3.png")
    if not os.path.isfile(bg3):
        print("MISSING bg3:", p)
        continue
    im = Image.open(bg3).convert("RGB").resize((TW, TH), Image.BILINEAR)
    cells.append((nn, p, im))

rows = (len(cells) + COLS - 1) // COLS
sheet = Image.new("RGB", (TW * COLS, (TH + 22) * rows), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, (nn, name, im) in enumerate(cells):
    cx, cy = (i % COLS) * TW, (i // COLS) * (TH + 22)
    sheet.paste(im, (cx, cy + 22))
    d.text((cx + 4, cy + 4), nn + "  " + name.replace("zzz_mindscape_", ""), fill=(255, 255, 120))
sheet.save(OUT)
print("saved", OUT, sheet.size, "projects:", len(cells))
