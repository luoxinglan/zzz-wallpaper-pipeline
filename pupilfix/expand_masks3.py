# -*- coding: utf-8 -*-
"""第二批 v3：描线定位 -> bg2 虹膜本体实测 -> 蒙版=虹膜形状，fallback=手工瞳色。
修 v1 两 bug：center_of_mass (y,x) 误用；细环平滑消失。"""
import numpy as np
from PIL import Image
from scipy import ndimage
import os, json, sys
sys.path.insert(0, r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix")
from bake_trace import dirs_of, RES, TM, QC

BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
BK = r"C:\Users\25485\.zcode\workspace\default\temp\we_v41_trace_backup"
CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40"
SHOTS = {
    "06": "image-454fd2f0c4e1c279965d512a1daa27f3.png",
    "07": "image-ee3a9c2eebd3c8eb7f7a4e0425f18547.png",
    "08": "image-aff5e418adffd2feb909798e43a6ab75.png",
    "13": "image-97c012fdec1cc043a126ac97e90ecc96.png",
}
# 描线屏幕质心（按 x 排序：左眼在前）
STROKES = {
    "06": [(15.39, 16.41), (22.13, 20.07)],
    "07": [(56.38, 35.70)],
    "08": [(48.27, 31.63)],
    "13": [(31.03, 27.23), (41.07, 22.26)],
}
# 候选锚位（图%），依序尝试：06 NCC 坏 -> 恒等优先；其余 PhaseA 优先
def cands(nn):
    res = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
    old = json.load(open(os.path.join(BK, "%d.json" % int(nn)), encoding="utf-8"))
    st = STROKES[nn]
    out = []
    for i, (sx, sy) in enumerate(st):
        pa = [(res["ax"], res["ay"]), (res["bx"], res["by"])][i] if len(st) == 2 else [(res["ax"], res["ay"])][0]
        ol = [(old["ax"], old["ay"]), (old["bx"], old["by"])][i] if len(st) == 2 else [(old["ax"], old["ay"])][0]
        c = [(sx, sy)] if nn == "06" else [pa]
        c += [(sx, sy)] if nn != "06" else []
        c += [ol]
        seen, cc = set(), []
        for t in c:
            k = (round(t[0],1), round(t[1],1))
            if k not in seen: seen.add(k); cc.append(t)
        out.append(cc)
    return out

def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i+2], 16) for i in (0, 2, 4)]) / 255.0

for nn in ("07", "08", "13"):
    d = dirs_of(nn)
    P = os.path.join(BASE, d)
    bg2_img = Image.open(os.path.join(P, "materials", "bg2.png"))
    W2, H2 = bg2_img.size
    bg2 = np.asarray(bg2_img.convert("RGB")).astype(float)
    mx = bg2.max(axis=2)/255
    mn = bg2.min(axis=2)/255
    sat = (mx-mn)/np.maximum(mx, 1e-6)
    res = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
    cols = [res.get("color_a", "#FFFFFF"), res.get("color_b", "#FFFFFF")]

    stroke_mask = np.asarray(Image.open(os.path.join(TM, "%s_mask.png" % nn))) > 127
    lab0, n0 = ndimage.label(stroke_mask)
    sblobs = [lab0 == k for k in range(1, n0+1) if int((lab0 == k).sum()) >= 300]
    sblobs.sort(key=lambda s: ndimage.center_of_mass(s)[1])
    assert len(sblobs) == len(STROKES[nn]), "%s stroke blobs=%d" % (nn, len(sblobs))

    print("== %s" % nn)
    final = np.zeros_like(stroke_mask)
    hand = [False, False]
    for i, (sb, st) in enumerate(zip(sblobs, STROKES[nn])):
        ys, xs = np.where(sb)
        mxs, mys = xs.mean(), ys.mean()
        found = False
        for (tx, ty) in cands(nn)[i]:
            placed = np.zeros_like(stroke_mask)
            txp, typ = tx/100*W2, ty/100*H2
            ixs = np.round(xs + (txp - mxs)).astype(int)
            iys = np.round(ys + (typ - mys)).astype(int)
            ok = (ixs>=0)&(ixs<W2)&(iys>=0)&(iys<H2)
            placed[iys[ok], ixs[ok]] = True
            placed = ndimage.binary_closing(placed, structure=np.ones((11,11)))
            placed = ndimage.binary_fill_holes(placed)
            wx0 = max(0, int((tx-3.2)/100*W2)); wx1 = min(W2, int((tx+3.2)/100*W2))
            wy0 = max(0, int((ty-3.2)/100*H2)); wy1 = min(H2, int((ty+3.2)/100*H2))
            win = np.zeros_like(stroke_mask); win[wy0:wy1, wx0:wx1] = True
            sdil = ndimage.binary_dilation(placed, iterations=9)
            blob = None
            for sthr in (0.30, 0.22, 0.16):
                m = (sat > sthr) & (mx > 0.18) & win
                lab, n = ndimage.label(m)
                best = None
                for k in range(1, n+1):
                    sel = lab == k; szz = int(sel.sum())
                    if szz < 150: continue
                    if int((sel & sdil).sum()) >= 15 and (best is None or szz > best[0]): best = (szz, sel)
                if best: blob = best; break
            if blob is None:  # 暗色块（灰蓝虹膜，07 类）
                m = (mx < 0.45) & win
                lab, n = ndimage.label(m)
                best = None
                for k in range(1, n+1):
                    sel = lab == k; szz = int(sel.sum())
                    if szz < 400: continue
                    if int((sel & sdil).sum()) >= 15 and (best is None or szz > best[0]): best = (szz, sel)
                if best: blob = best; hand[i] = True
            if blob:
                szz, bsel = blob
                mean = bg2[bsel].mean(axis=0).astype(int)
                print("  eye%d @cand(%.2f,%.2f) blob=%dpx rgb=%s hand=%s" % (i, tx, ty, szz, tuple(mean), hand[i]))
                final |= bsel
                final |= placed
                found = True
                break
        if not found:
            print("  eye%d ALL candidates failed -> fallback dilate+handcolor" % i)
            placed = ndimage.binary_dilation(placed, iterations=8)
            placed = ndimage.binary_closing(placed, structure=np.ones((11,11)))
            placed = ndimage.binary_fill_holes(placed)
            final |= placed
            hand[i] = True

    g = ndimage.gaussian_filter(final.astype(float), 4.0)
    final = g > 0.5
    Image.fromarray((final*255).astype(np.uint8)).save(os.path.join(TM, "%s_mask.png" % nn))
    bgv = np.asarray(bg2_img.convert("RGB")).copy()
    bgv[final] = (bgv[final]*0.35 + np.array([0,255,0])*0.65).astype(np.uint8)
    qim = Image.fromarray(bgv); qim.thumbnail((1500,1500), Image.LANCZOS)
    qim.save(os.path.join(QC, "%s_tracemapped.png" % nn))

    comps2 = []
    lab2, n2 = ndimage.label(final)
    for k in range(1, n2+1):
        sel = lab2 == k; szz = int(sel.sum())
        if szz >= 300:
            cy, cx = ndimage.center_of_mass(sel)
            comps2.append((round(cx/W2*100,2), round(cy/H2*100,2), szz))
    comps2.sort()
    print("  blobs:", comps2)
    assert comps2, nn + " final mask empty"
    res["ax"], res["ay"] = comps2[0][0], comps2[0][1]
    if len(comps2) >= 2: res["bx"], res["by"] = comps2[1][0], comps2[1][1]
    else: res["bx"], res["by"] = res["ax"], res["ay"]
    json.dump(res, open(os.path.join(RES, "%d.json" % int(nn)), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    alpha = ndimage.gaussian_filter(final.astype(float), 1.8)
    alpha = np.clip(alpha*1.35, 0, 1)
    rgb = np.clip(bg2*1.35/255.0, 0, 1)
    mxch = bg2.max(axis=2, keepdims=True)
    colnorm = bg2/np.maximum(mxch, 1e-6)
    rgb = np.maximum(rgb, colnorm*0.45)
    if any(hand):
        hc = hex2rgb(cols[0] if hand[0] else cols[1])
        hc = np.clip(hc*1.35, 0, 1)
        rgb = np.where(np.array(hand, dtype=object).reshape(1,1,2), 0, 0)  # placeholder no-op
        # 手工色只铺 hand 眼的 blob 区域
        lab3, n3 = ndimage.label(final)
        for k in range(1, n3+1):
            sel = lab3 == k
            if int(sel.sum()) < 300: continue
            cy, cx = ndimage.center_of_mass(sel)
            idx = 0 if cx < W2/2 or len(comps2) == 1 else 1
            if hand[idx] if idx < 2 else False:
                rgb[sel] = hc.reshape(1,3)
        print("  handcolor bake:", hc)
    rgba = (np.dstack([rgb*alpha[...,None], alpha[...,None]])*255).astype(np.uint8)
    Image.fromarray(rgba).save(os.path.join(P, "materials", "eyeglow.png"))
    import rebake_v41c as _rb
    _rb._recycle_tex(P)
    import apply_v41b
    print("  apply:", apply_v41b.apply_project(d))
