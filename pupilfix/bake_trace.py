# -*- coding: utf-8 -*-
"""v41l 描线烘焙：用户手绘轮廓 → 填充 → NCC 对齐映射到 bg2 → 按轮廓烘焙（轻羽化）
用法：python bake_trace.py   （JOBS 表内 5 个项目）
覆盖 circle_overrides：这些项目的蒙版存 trace_masks/NN.png，此后 rebake_v41c 检测到该文件直接用它。
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.signal import fftconvolve

CACHE = r"C:\Users\25485\.zcode\cli\image-cache\sess_7c1f9ba4-0784-4f14-87ee-9e44243ea8ef"
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
RES = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\results"
QC = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\qc_v41c"
TM = r"C:\Users\25485\.zcode\workspace\default\temp\pupilfix\trace_masks"
os.makedirs(TM, exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 描边笔颜色库（min RGB, max RGB）——用户截图里出现的纯色笔迹
PALETTES = {
    "cyan": ((0, 150, 180), (120, 225, 255)),     # 青色笔
    "lime": ((90, 170, 0), (190, 240, 110)),      # 青柠绿笔
    "red":  ((180, 0, 0), (255, 110, 110)),       # 红笔
    "blue": ((0, 60, 200), (130, 160, 255)),      # 蓝笔
    "azure": ((0, 140, 210), (90, 210, 255)),     # 亮蓝笔(0,168,240)，避开青绿画作
    "gold":  ((210, 180, 0), (255, 230, 80)),     # 金黄笔(240,192,0)，伊芙琳专用，B≤80 排除淡黄画作
}
# 历史批次（可复跑）：nn -> (截图文件, 颜色, 双眼屏幕%, img先验%)
JOBS = {
    "17": ("image-189ef6c52e3234a794d69f0af14590cc.png", "lime", [(38.5, 27.6), (35.7, 41.3)], (40.0, 33.0)),
    "18": ("image-45e0104edb6d8d8bb11c5336ca1052e5.png", "cyan", [(59.8, 34.8), (62.3, 48.3)], (60.0, 41.0)),
    "23": ("image-077b9d52823af84086b8198998d0ce65.png", "cyan", [(22.76, 36.11), (33.99, 39.88)], (29.0, 37.5)),
    "13": ("image-a344aa4f1ff900d44d544a092dcdd23b.png", "cyan", [(30.81, 27.33), (41.00, 22.48)], (36.0, 25.0)),
    "16": ("image-eb76ddb8cfd10b9e09ba0617ac97b0be.png", "lime", [(30.49, 32.41), (38.22, 47.26)], (34.5, 40.0)),
    # 2026-10-18 批次（sess_0d24efd0 截图；26 扳机用户中途取消不做）
    "67": (r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40\image-b572d221420f6a98f399222228cedfa8.png",
           "red", [(55.9, 48.0)], (55.0, 48.5)),
    "01": (r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40\image-8e1ea44b1c18e963ebda8193031fb2fc.png",
           "azure", [(54.8, 27.3), (44.1, 31.8)], (48.4, 30.3)),
    "02": (r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40\image-b369de3f5133fc76f677b2172b51c517.png",
           "red", [(72.6, 25.7), (66.9, 24.8)], (67.9, 26.8)),
    "04": (r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40\image-e5cdd7cf95cb3d6ed365173857513a28.png",
           "azure", [(29.8, 31.5), (19.5, 40.2)], (26.1, 36.4)),
    "05": (r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40\image-67c60bd2b8451a08ac5922c410e10445.png",
           "lime", [(82.2, 29.2), (75.0, 26.4)], (75.4, 29.1)),
    # 2026-10-18 晚第二批（描线小于真眼，Phase B 需扩到虹膜本体）
    "06": (r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40\image-454fd2f0c4e1c279965d512a1daa27f3.png",
           "gold", [(15.4, 16.4), (22.1, 20.1)], (20.2, 19.9)),
    "07": (r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40\image-ee3a9c2eebd3c8eb7f7a4e0425f18547.png",
           "red", [(56.4, 35.7)], (54.7, 36.8)),
    "08": (r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40\image-aff5e418adffd2feb909798e43a6ab75.png",
           "azure", [(48.3, 31.6)], (47.8, 32.1)),
    "13": (r"C:\Users\25485\.zcode\cli\image-cache\sess_0d24efd0-2e5c-4ce8-b1ed-bbec60bc0f40\image-97c012fdec1cc043a126ac97e90ecc96.png",
           "lime", [(31.0, 27.2), (41.1, 22.3)], (37.5, 26.0)),
}

def ncc_match(region, templ):
    t = templ - templ.mean()
    r = region - region.mean()
    num = fftconvolve(r, t[::-1, ::-1], mode="valid")
    ones = np.ones_like(t)
    s1 = fftconvolve(r*r, ones[::-1, ::-1], mode="valid")
    var = s1 - num**2/t.size
    var[var < 1e-6] = 1e-6
    ncc = num/np.sqrt(var*(t*t).sum())
    y, x = np.unravel_index(np.argmax(ncc), ncc.shape)
    return ncc[y, x], y, x

def dirs_of(nn):
    for d in os.listdir(BASE):
        if d.startswith("zzz_mindscape_%s_" % nn): return d

def auto_color(shot):
    """自动识别描边笔颜色：组件尺寸像笔画(400~40000px)且组数>=1 的调色板，取组件像素最多者"""
    from scipy import ndimage as _nd
    best = (0, None)
    for name, ((r0, g0, b0), (r1, g1, b1)) in PALETTES.items():
        R, G, B = shot[...,0], shot[...,1], shot[...,2]
        m = (R>=r0)&(R<=r1)&(G>=g0)&(G<=g1)&(B>=b0)&(B<=b1)
        lab, n = _nd.label(m)
        px = 0
        for k in range(1, n+1):
            s = int((lab==k).sum())
            if 400 <= s <= 40000: px += s
        if px > best[0]:
            best = (px, name)
    return best[1]

def process(nn, shot_file, color="auto", eyes=None, prior_img=None, minpix=400, searchr=(18, 19)):
    d = dirs_of(nn)
    P = os.path.join(BASE, d)
    shot_path = shot_file if os.path.isabs(shot_file) else os.path.join(CACHE, shot_file)
    shot = np.asarray(Image.open(shot_path).convert("RGB")).astype(int)
    H1, W1 = shot.shape[:2]
    if color == "auto":
        color = auto_color(shot)
        print(f"{nn}: auto color -> {color}")
    (r0, g0, b0), (r1, g1, b1) = PALETTES[color]
    res0 = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
    if not prior_img:
        prior_img = ((res0["ax"]+res0["bx"])/2, (res0["ay"]+res0["by"])/2)
    R, G, B = shot[...,0], shot[...,1], shot[...,2]
    trace = (R >= r0) & (R <= r1) & (G >= g0) & (G <= g1) & (B >= b0) & (B <= b1)
    trace = ndimage.binary_closing(trace, structure=np.ones((7, 7)))
    lab, n = ndimage.label(trace)
    keep = np.zeros_like(trace)
    comps = []
    for k in range(1, n+1):
        sel = lab == k; sz = int(sel.sum())
        if sz < minpix or sz > 40000: continue
        cy, cx = ndimage.center_of_mass(sel)
        scx, scy = cx/W1*100, cy/H1*100
        if eyes and not any(abs(scx-e[0]) < 7 and abs(scy-e[1]) < 7 for e in eyes):
            continue  # 给了先验就只留眼部区域的描线
        keep |= sel; comps.append((sz, scx, scy))
    comps.sort(key=lambda c: -c[0])
    print(f"{nn}: kept comps={len(comps)} {comps[:4]}")
    if not comps:
        return nn + " TRACE-NOT-FOUND"
    trace = keep
    trace = ndimage.binary_closing(trace, iterations=12)   # 封住开口
    trace = ndimage.binary_fill_holes(trace)
    trace = ndimage.binary_dilation(trace, iterations=3)   # 轻扩保证盖满

    # NCC 平移对齐：模板=描线 bbox 外扩 1.6x 的截图区域（描线像素用中值替换去伪）
    ys, xs = np.where(keep)
    bx0, bx1 = xs.min(), xs.max(); by0, by1 = ys.min(), ys.max()
    mx, my = (bx0+bx1)//2, (by0+by1)//2
    ext = min(220, max(bx1-bx0, by1-by0) * 0.8 + 120)
    tx0, tx1 = max(0, int(mx-ext)), min(W1, int(mx+ext))
    ty0, ty1 = max(0, int(my-ext)), min(H1, int(my+ext))
    tmpl_rgb = shot[ty0:ty1, tx0:tx1].astype(float)
    tr = keep[ty0:ty1, tx0:tx1]
    med = ndimage.median_filter(tmpl_rgb, size=(9, 9, 1))
    tmpl_rgb[tr] = med[tr]
    tmpl = tmpl_rgb.mean(axis=2)
    ch, cw = tmpl.shape
    W2 = Image.open(os.path.join(P, "materials", "bg2.png")).size[0]
    scale = H_s = None
    bg2_img = Image.open(os.path.join(P, "materials", "bg2.png"))
    W2, H2 = bg2_img.size
    sx_scale = W2 / (H1 * W2 / H2)  # = H2/H1
    sy_scale = H2 / H1
    tmpl_img = np.asarray(Image.fromarray(tmpl.astype(np.uint8)).resize(
        (int(cw*sx_scale), int(ch*sy_scale)), Image.LANCZOS)).astype(float)
    bg2 = np.asarray(bg2_img.convert("L")).astype(float)
    ex, ey = int(prior_img[0]/100*W2), int(prior_img[1]/100*H2)
    rx, ry = int(searchr[0]/100*W2), int(searchr[1]/100*H2)
    x0, x1 = max(0, ex-rx), min(W2, ex+rx)
    y0, y1 = max(0, ey-ry), min(H2, ey+ry)
    region = bg2[y0:y1, x0:x1]
    ncc, yy, xx = ncc_match(region, tmpl_img)
    # 平移：模板左上角在 bg2 的 (x0+xx, y0+yy)；模板左上角在截图的 (tx0,ty0)
    off_x = (x0 + xx) - tx0 * sx_scale
    off_y = (y0 + yy) - ty0 * sy_scale
    print(f"{nn}: ncc={ncc:.3f} offset=({off_x:.0f},{off_y:.0f})")

    # 映射描线蒙版到原生画布
    mask = np.zeros((H2, W2), bool)
    ys, xs = np.where(keep)
    ixs = (xs * sx_scale + off_x).astype(int)
    iys = (ys * sy_scale + off_y).astype(int)
    ok = (ixs >= 0) & (ixs < W2) & (iys >= 0) & (iys < H2)
    mask[iys[ok], ixs[ok]] = True
    mask = ndimage.binary_closing(mask, structure=np.ones((9, 9)))
    mask = ndimage.binary_fill_holes(mask)
    # 轮廓平滑：高斯 σ5 再阈值 0.5（去手抖与映射锯齿，不缩区域）
    g = ndimage.gaussian_filter(mask.astype(float), 5.0)
    mask = g > 0.5

    # 保存蒙版 + QC 叠加
    Image.fromarray((mask*255).astype(np.uint8)).save(os.path.join(TM, "%s_mask.png" % nn))
    bgv = np.asarray(bg2_img.convert("RGB")).copy()
    bgv[mask] = (bgv[mask]*0.35 + np.array([0,255,0])*0.65).astype(np.uint8)
    qim = Image.fromarray(bgv); qim.thumbnail((1500,1500), Image.LANCZOS)
    qim.save(os.path.join(QC, "%s_tracemapped.png" % nn))

    # 质心 → results
    res = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
    comps2 = []
    lab2, n2 = ndimage.label(mask)
    for k in range(1, n2+1):
        sel = lab2 == k; sz = int(sel.sum())
        if sz >= 300:
            cy, cx = ndimage.center_of_mass(sel)
            comps2.append((cx/W2*100, cy/H2*100, sz))
    comps2.sort()
    if len(comps2) >= 2:
        res["ax"], res["ay"] = round(comps2[0][0],2), round(comps2[0][1],2)
        res["bx"], res["by"] = round(comps2[1][0],2), round(comps2[1][1],2)
    elif comps2:
        res["ax"], res["ay"] = round(comps2[0][0],2), round(comps2[0][1],2)
        res["bx"], res["by"] = res["ax"], res["ay"]
    json.dump(res, open(os.path.join(RES, "%d.json" % int(nn)), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 烘焙：轻羽化 + 暗像素保底
    bg2f = np.asarray(bg2_img.convert("RGB")).astype(float)/255
    alpha = ndimage.gaussian_filter(mask.astype(float), 1.8)
    alpha = np.clip(alpha*1.35, 0, 1)
    rgb = np.clip(bg2f*1.35, 0, 1)
    mxch = bg2f.max(axis=2, keepdims=True)
    colnorm = bg2f/np.maximum(mxch, 1e-6)
    rgb = np.maximum(rgb, colnorm*0.45)
    rgba = (np.dstack([rgb*alpha[...,None], alpha[...,None]])*255).astype(np.uint8)
    Image.fromarray(rgba).save(os.path.join(P, "materials", "eyeglow.png"))

    import rebake_v41c as _rb
    _rb._recycle_tex(P)
    import apply_v41b
    try:
        msg = apply_v41b.apply_project(d)
    except AssertionError as e:
        msg = "ASSERT:%s" % e
    return "%s | %s" % (" ".join("A(%.1f,%.1f)" % comps2[0][:2] for _ in [0]) if comps2 else "", str(msg)[:60])

def sync_project(nn):
    import subprocess
    CFGP = "E:/Program Files (x86)/Steam/steamapps/common/wallpaper_engine/config.json"
    for exe in ("wallpaper64.exe","wallpaper32.exe","wallpaperui.exe"):
        subprocess.run(["taskkill","/F","/IM",exe], capture_output=True)
    import time as _t; _t.sleep(6.5)
    cfg = json.load(open(CFGP, encoding="utf-8"))
    r = json.load(open(os.path.join(RES, "%d.json" % int(nn)), encoding="utf-8"))
    P = os.path.join(BASE, dirs_of(nn))
    vals = {"pupulseax": r["ax"], "pupulseay": r["ay"], "pupulsebx": r["bx"], "pupulseby": r["by"]}
    key = P.replace(os.sep,"/") + "/scene.json"
    cfg["25485"]["wproperties"].setdefault(key, {}).setdefault("Monitor0", {}).update(vals)
    pj = json.load(open(os.path.join(P, "project.json"), encoding="utf-8"))
    for k, v in vals.items():
        if k in pj["general"]["properties"]: pj["general"]["properties"][k]["value"] = v
    tmp = os.path.join(P, "project.json") + ".tmp"
    json.dump(pj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent="	")
    os.replace(tmp, os.path.join(P, "project.json"))
    tmp = CFGP + ".tmp"
    json.dump(cfg, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent="	")
    os.replace(tmp, CFGP)
    print(nn, "synced (config+defaults)")
    WEROOT = "E:/Program Files (x86)/Steam/steamapps/common/wallpaper_engine"
    subprocess.Popen([os.path.join(WEROOT, "wallpaper32.exe")], cwd=WEROOT)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj")
    ap.add_argument("--shot")
    ap.add_argument("--color", default="auto")
    ap.add_argument("--eyes", default="")     # "sx,sy;sx,sy" 屏幕%
    ap.add_argument("--prior", default="")    # "x,y" 图%
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--jobs", action="store_true", help="复跑历史批次")
    ap.add_argument("--minpix", type=int, default=400)
    ap.add_argument("--searchr", default="")  # "18,19" NCC 搜索窗半径（图%）
    a = ap.parse_args()
    sr = tuple(float(v) for v in a.searchr.split(",")) if a.searchr else (18, 19)
    if a.jobs:
        for nn, (sf, col, eyes, prior) in JOBS.items():
            print(nn, "->", process(nn, sf, col, eyes, prior, minpix=a.minpix, searchr=sr))
    else:
        eyes = [tuple(map(float, p.split(","))) for p in a.eyes.split(";") if p] or None
        prior = tuple(map(float, a.prior.split(","))) if a.prior else None
        print(a.proj, "->", process(a.proj, a.shot, a.color, eyes, prior, minpix=a.minpix, searchr=sr))
        if a.sync:
            sync_project(a.proj)
