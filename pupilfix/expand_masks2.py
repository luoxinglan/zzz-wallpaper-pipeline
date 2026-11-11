# -*- coding: utf-8 -*-
"""第二批（06/07/08/13）：描线小于真眼 -> 描线定位，蒙版扩到 bg2 虹膜本体
06 的 NCC 锁错峰 -> 用备份旧真值锚定；其余用 Phase A 映射位置。
最终蒙版 = 实测虹膜色块(与描线重叠者) ∪ 描线填充，平滑后重烘焙+apply。
"""
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
# 描线屏幕质心（Phase A 输出），按 blob x 排序后对应 [A(左), B(右)]
STROKES = {
    "06": [(22.13, 20.07), (15.39, 16.41)],   # A=右眼(22.1), B=左眼(15.4)
    "07": [(56.38, 35.70)],
    "08": [(48.27, 31.63)],
    "13": [(31.03, 27.23), (41.07, 22.26)],
}
# 锚定目标（图%）：06 用旧真值（NCC 锁错），其余用 Phase A results（读文件）
ANCHOR_OLD = {"06": True}

def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i+2], 16) for i in (0, 2, 4)]) / 255.0

for nn in ("06", "07", "08", "13"):
    d = dirs_of(nn)
    P = os.path.join(BASE, d)
    bg2_img = Image.open(os.path.join(P, "materials", "bg2.png"))
    W2, H2 = bg2_img.size
    shot = np.asarray(Image.open(os.path.join(CACHE, SHOTS[nn])).convert("RGB")).astype(int)
    H1, W1 = shot.shape[:2]
    sc = H2 / H1

    if ANCHOR_OLD.get(nn):
        old = json.load(open(os.path.join(BK, "%d.json" % int(nn)), encoding="utf-8"))
        targets = [(old["ax"], old["ay"]), (old["bx"], old["by"])]
    else:
        res0 = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
        targets = [(res0["ax"], res0["ay"]), (res0["bx"], res0["by"])][:len(STROKES[nn])]

    # 描线蒙版（trace_masks 里的 Phase A 产物，即映射后的描线填充）
    stroke_mask = np.asarray(Image.open(os.path.join(TM, "%s_mask.png" % nn))) > 127
    lab0, n0 = ndimage.label(stroke_mask)
    sblobs = [lab0 == k for k in range(1, n0+1) if int((lab0 == k).sum()) >= 300]
    sblobs.sort(key=lambda s: ndimage.center_of_mass(s)[1])
    assert len(sblobs) == len(STROKES[nn]), "%s stroke blobs=%d" % (nn, len(sblobs))

    bg2 = np.asarray(bg2_img.convert("RGB")).astype(float)
    mx = bg2.max(axis=2)/255; mn = bg2.min(axis=2)/255
    sat = (mx-mn)/np.maximum(mx, 1e-6)

    print("== %s" % nn)
    final = np.zeros_like(stroke_mask)
    handcolor = None
    for i, (sb, (sx, sy)) in enumerate(zip(sblobs, STROKES[nn])):
        tx, ty = targets[i]
        # 描线 blob 平移到锚定目标
        ys, xs = np.where(sb)
        cx0, cy0 = ndimage.center_of_mass(sb)
        txp, typ = tx/100*W2, ty/100*H2
        ixs = np.round(xs + (txp - cx0)).astype(int)
        iys = np.round(ys + (typ - cy0)).astype(int)
        ok = (ixs>=0)&(ixs<W2)&(iys>=0)&(iys<H2)
        placed = np.zeros_like(stroke_mask)
        placed[iys[ok], ixs[ok]] = True
        # 实测虹膜色块：目标±3% 窗口内，与描线(扩9px)重叠的饱和色块
        wx0, wx1 = max(0,int(tx-3.0)/100*W2), min(W2,int(tx+3.0)/100*W2)
        wy0, wy1 = max(0,int(ty-3.0)/100*H2), min(H2,int(ty+3.0)/100*H2)
        wx0, wx1, wy0, wy1 = int(wx0), int(wx1), int(wy0), int(wy1)
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
                ov = int((sel & sdil).sum())
                if ov >= 20 and (best is None or szz > best[0]): best = (szz, sel)
            if best: blob = best; break
        if blob:
            szz, bsel = blob
            mean = bg2[bsel].mean(axis=0).astype(int)
            print("  eye%d target(%.2f,%.2f) iris blob=%dpx rgb=%s sat=%.2f" % (
                i, tx, ty, szz, tuple(mean), sthr))
            final |= bsel
        else:
            print("  eye%d target(%.2f,%.2f) NO iris blob -> stroke dilate fallback" % (i, tx, ty))
            final |= ndimage.binary_dilation(placed, iterations=7)
            if nn == "07":
                handcolor = hex2rgb("#686DF0")  # v41i 手工亮蓝（bg2 眼区灰蓝）
        final |= placed

    # 平滑 + 保存
    g = ndimage.gaussian_filter(final.astype(float), 4.0)
    final = g > 0.5
    Image.fromarray((final*255).astype(np.uint8)).save(os.path.join(TM, "%s_mask.png" % nn))
    bgv = np.asarray(bg2_img.convert("RGB")).copy()
    bgv[final] = (bgv[final]*0.35 + np.array([0,255,0])*0.65).astype(np.uint8)
    qim = Image.fromarray(bgv); qim.thumbnail((1500,1500), Image.LANCZOS)
    qim.save(os.path.join(QC, "%s_tracemapped.png" % nn))

    # results = 新质心
    res = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
    comps2 = []
    lab2, n2 = ndimage.label(final)
    for k in range(1, n2+1):
        sel = lab2 == k; szz = int(sel.sum())
        if szz >= 300:
            cy, cx = ndimage.center_of_mass(sel)
            comps2.append((round(cx/W2*100,2), round(cy/H2*100,2), szz))
    comps2.sort()
    print("  blobs:", comps2)
    res["ax"], res["ay"] = comps2[0][0], comps2[0][1]
    if len(comps2) >= 2: res["bx"], res["by"] = comps2[1][0], comps2[1][1]
    else: res["bx"], res["by"] = res["ax"], res["ay"]
    json.dump(res, open(os.path.join(RES, "%d.json" % int(nn)), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 烘焙（07 fallback 时手工色）
    alpha = ndimage.gaussian_filter(final.astype(float), 1.8)
    alpha = np.clip(alpha*1.35, 0, 1)
    rgb = np.clip(bg2*1.35/255.0, 0, 1)
    mxch = bg2.max(axis=2, keepdims=True)
    colnorm = bg2/np.maximum(mxch, 1e-6)
    rgb = np.maximum(rgb, colnorm*0.45)
    if handcolor is not None:
        hc = np.clip(handcolor*1.35, 0, 1)
        rgb = np.ones_like(rgb) * hc.reshape(1,1,3)
        print("  bake with handcolor", hc)
    rgba = (np.dstack([rgb*alpha[...,None], alpha[...,None]])*255).astype(np.uint8)
    Image.fromarray(rgba).save(os.path.join(P, "materials", "eyeglow.png"))
    import rebake_v41c as _rb
    _rb._recycle_tex(P)
    import apply_v41b
    print("  apply:", apply_v41b.apply_project(d))
