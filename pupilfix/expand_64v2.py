# -*- coding: utf-8 -*-
"""64 雨果恢复版：最近旧锚 + 左眼低阈（=v41n-e 验收态）"""
import numpy as np
from PIL import Image
from scipy import ndimage
import os, json, sys
sys.path.insert(0, r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix")
from bake_trace import dirs_of, RES, TM, QC

BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
BK = r"C:\Users\25485\.zcode\workspace\default\temp\we_v41_trace_backup"
STROKES = [(49.4, 22.8), (58.3, 26.5)]

nn = "64"
d = dirs_of(nn)
P = os.path.join(BASE, d)
bg2_img = Image.open(os.path.join(P, "materials", "bg2.png"))
W2, H2 = bg2_img.size
bg2 = np.asarray(bg2_img.convert("RGB")).astype(float)
mx = bg2.max(axis=2) / 255
sat = (mx - bg2.min(axis=2) / 255) / np.maximum(mx, 1e-6)
res = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
old = json.load(open(os.path.join(BK, "%d.json" % int(nn)), encoding="utf-8"))
oldeyes = [(old["ax"], old["ay"]), (old["bx"], old["by"])]

stroke_mask = np.asarray(Image.open(os.path.join(TM, "%s_mask.png" % nn))) > 127
lab0, n0 = ndimage.label(stroke_mask)
sblobs = [lab0 == k for k in range(1, n0 + 1) if int((lab0 == k).sum()) >= 300]
sblobs.sort(key=lambda s: ndimage.center_of_mass(s)[1])
assert len(sblobs) == 2, "stroke blobs=%d" % len(sblobs)

final = np.zeros_like(stroke_mask)
hand = [False, False]
for i, (sb, (sx, sy)) in enumerate(zip(sblobs, STROKES)):
    ys, xs = np.where(sb)
    mxs, mys = xs.mean(), ys.mean()
    pa = [(res["ax"], res["ay"]), (res["bx"], res["by"])][i]
    ol = min(oldeyes, key=lambda t: (t[0]-sx)**2 + (t[1]-sy)**2)
    cands_, seen = [], set()
    for t in [pa, (sx, sy), ol]:
        k = (round(t[0], 1), round(t[1], 1))
        if k not in seen:
            seen.add(k)
            cands_.append(t)
    found = False
    for (tx, ty) in cands_:
        placed = np.zeros_like(stroke_mask)
        txp, typ = tx / 100 * W2, ty / 100 * H2
        ixs = np.round(xs + (txp - mxs)).astype(int)
        iys = np.round(ys + (typ - mys)).astype(int)
        ok = (ixs >= 0) & (ixs < W2) & (iys >= 0) & (iys < H2)
        placed[iys[ok], ixs[ok]] = True
        placed = ndimage.binary_closing(placed, structure=np.ones((11, 11)))
        placed = ndimage.binary_fill_holes(placed)
        rad = 2.2 if i == 0 else 3.2
        wx0 = max(0, int((tx-rad)/100*W2)); wx1 = min(W2, int((tx+rad)/100*W2))
        wy0 = max(0, int((ty-rad)/100*H2)); wy1 = min(H2, int((ty+rad)/100*H2))
        win = np.zeros_like(stroke_mask)
        win[wy0:wy1, wx0:wx1] = True
        sdil = ndimage.binary_dilation(placed, iterations=9)
        blob = None
        thrs = (0.22, 0.16, 0.10) if i == 0 else (0.30, 0.22, 0.16)
        minp = 100 if i == 0 else 150
        for sthr in thrs:
            m = (sat > sthr) & (mx > 0.18) & win
            lab, n = ndimage.label(m)
            best = None
            for k in range(1, n + 1):
                sel = lab == k
                szz = int(sel.sum())
                if szz < minp:
                    continue
                if int((sel & sdil).sum()) >= 15 and (best is None or szz > best[0]):
                    best = (szz, sel)
            if best:
                blob = best
                break
        if blob:
            szz, bsel = blob
            mean = bg2[bsel].mean(axis=0).astype(int)
            print("  eye%d @cand(%.2f,%.2f) blob=%dpx rgb=%s" % (i, tx, ty, szz, tuple(mean)))
            final |= bsel
            final |= placed
            found = True
            break
    if not found:
        print("  eye%d fallback -> handcolor" % i)
        placed = ndimage.binary_dilation(placed, iterations=6)
        placed = ndimage.binary_closing(placed, structure=np.ones((11, 11)))
        placed = ndimage.binary_fill_holes(placed)
        final |= placed
        hand[i] = True

g = ndimage.gaussian_filter(final.astype(float), 4.0)
final = g > 0.5
Image.fromarray((final * 255).astype(np.uint8)).save(os.path.join(TM, "%s_mask.png" % nn))
bgv = np.asarray(bg2_img.convert("RGB")).copy()
bgv[final] = (bgv[final] * 0.35 + np.array([0, 255, 0]) * 0.65).astype(np.uint8)
qim = Image.fromarray(bgv)
qim.thumbnail((1500, 1500), Image.LANCZOS)
qim.save(os.path.join(QC, "%s_tracemapped.png" % nn))

comps2 = []
lab2, n2 = ndimage.label(final)
for k in range(1, n2 + 1):
    sel = lab2 == k
    szz = int(sel.sum())
    if szz >= 300:
        cy, cx = ndimage.center_of_mass(sel)
        comps2.append((round(cx / W2 * 100, 2), round(cy / H2 * 100, 2), szz))
comps2.sort()
print("  blobs:", comps2)
assert len(comps2) == 2, "expect 2, got %d" % len(comps2)
res["ax"], res["ay"] = comps2[0][0], comps2[0][1]
res["bx"], res["by"] = comps2[1][0], comps2[1][1]
json.dump(res, open(os.path.join(RES, "%d.json" % int(nn)), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

alpha = ndimage.gaussian_filter(final.astype(float), 1.8)
alpha = np.clip(alpha * 1.35, 0, 1)
rgb = np.clip(bg2 * 1.35 / 255.0, 0, 1)
mxch = bg2.max(axis=2, keepdims=True)
colnorm = bg2 / np.maximum(mxch, 1e-6)
rgb = np.maximum(rgb, colnorm * 0.45)
rgba = (np.dstack([rgb * alpha[..., None], alpha[..., None]]) * 255).astype(np.uint8)
Image.fromarray(rgba).save(os.path.join(P, "materials", "eyeglow.png"))
import rebake_v41c as _rb
_rb._recycle_tex(P)
import apply_v41b
print("  apply:", apply_v41b.apply_project(d))
