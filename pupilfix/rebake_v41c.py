# -*- coding: utf-8 -*-
"""v41c 眼形光斑重烘焙：逐眼局部虹膜检测（bg2），修三类病灶
1) 区域不对（头发/睫毛/眼白混入）→ 连通域+腐蚀断桥+紧凑度筛选，只留虹膜
2) 位置不对 → 窗口内重定心（结果写回 results/NN.json）
3) 单眼缺失 → 每眼独立检测；bx==ax 塌缩项目出面部大图人工补第二眼坐标
产出：QC 对照图 temp/pupilfix/qc_v41c/NN.png（上=A眼 下=B眼：bg2裁剪|叠加|烤片）
写回：eyeglow.png(原生画布) + results/NN.json 精化坐标，然后调 apply_v41b.apply_project 完成垫底/frag/绑定/顺序
"""
import json, os, sys, importlib
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

TEMP = r"C:\Users\25485\.zcode\workspace\default\temp"
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
RESULTS = os.path.join(TEMP, "pupilfix", "results")
QC = os.path.join(TEMP, "pupilfix", "qc_v41c")
os.makedirs(QC, exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def dirs_of(nn):
    for d in os.listdir(BASE):
        if d.startswith("zzz_mindscape_%s_" % nn):
            return d
    raise FileNotFoundError(nn)

def detect_iris(bg2, ex, ey, seed_r_px):
    """窗口内局部检测（v41c2：种子包含判定+主色相过滤+全阈值寻优+宽松回长）
    返回 (mask全图坐标, info dict)。失败返回 (None, reason)"""
    H, W = bg2.shape[:2]
    mx = bg2.max(axis=2); mn = bg2.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    exf, eyf = ex / 100 * W, ey / 100 * H
    hw = int(min(max(W * 0.025, seed_r_px * 2.2), W * 0.045))
    x0, x1 = int(exf) - hw, int(exf) + hw
    y0, y1 = int(eyf) - hw, int(eyf) + hw
    x0c, y0c = max(0, x0), max(0, y0)
    x1c, y1c = min(W, x1), min(H, y1)
    win = np.zeros((H, W), bool)
    win[y0c:y1c, x0c:x1c] = True

    def hue_of(px):
        r, g, b = px[..., 0], px[..., 1], px[..., 2]
        return np.arctan2(np.sqrt(3.0) * (g - b), 2 * r - g - b)  # -pi..pi

    best = None
    for sath in (0.28, 0.22, 0.16, 0.12, 0.09):
        for valh in (0.13, 0.08):
            m = (sat > sath) & (mx > valh) & win
            if m.sum() < 40:
                continue
            core = ndimage.binary_erosion(m, iterations=2)  # 断开睫毛/发丝细桥
            lab, n = ndimage.label(core)
            for k in range(1, n + 1):
                comp = lab == k
                sz = int(comp.sum())
                if sz < 30:
                    continue
                cy, cx = ndimage.center_of_mass(comp)
                d = float(np.hypot(cx - exf, cy - eyf))
                if d > hw * 0.85:
                    continue
                ys0, xs0 = np.where(comp)
                if min(np.hypot(xs0 - exf, ys0 - eyf)) > hw * 0.60:
                    continue  # 成分必须触到种子附近（防远处头发/眉毛胜出）
                grow = ndimage.binary_dilation(comp, iterations=2) & m
                # 宽松回长：更低阈值把虹膜暗部收进来
                looser = (sat > max(sath - 0.06, 0.05)) & (mx > valh) & win
                for _ in range(6):
                    g2 = ndimage.binary_dilation(grow, iterations=2) & looser
                    if g2.sum() == grow.sum():
                        break
                    grow = g2
                grow = ndimage.binary_fill_holes(grow)
                ys, xs = np.where(grow)
                gh, gw = int(ys.max() - ys.min()) + 1, int(xs.max() - xs.min()) + 1
                ar = gh / max(gw, 1)
                if ar > 3.5 or ar < 0.29:
                    continue
                if max(gh, gw) > hw * 1.5:
                    continue
                # 主色相过滤：核心中位色相 ±60° 之外的丢掉（黄睫毛/异色眼影）
                hp = hue_of(bg2[comp])
                med = np.arctan2(np.sin(hp).mean(), np.cos(hp).mean())
                gp = hue_of(bg2[grow])
                dh = np.abs((gp - med + np.pi) % (2 * np.pi) - np.pi)
                keep = dh <= np.radians(60)
                if keep.sum() >= 0.5 * grow.sum() and keep.sum() > 30:
                    g3 = np.zeros_like(grow)
                    g3[grow] = keep
                    g3 = ndimage.binary_closing(g3, structure=np.ones((3, 3)))
                    if g3.sum() > 30:
                        grow = ndimage.binary_fill_holes(g3)
                sz2 = int(grow.sum())
                cy2, cx2 = ndimage.center_of_mass(grow)
                d2 = float(np.hypot(cx2 - exf, cy2 - eyf))
                score = sz2 * float(np.exp(-(d2 / (hw * 0.30)) ** 2))
                if best is None or score > best[0]:
                    best = (score, grow, cx2, cy2, sz2, sath)
    if best is None:
        return None, "no-component"
    _, mask, cx, cy, sz, sath = best
    r_eq = float(np.sqrt(sz / np.pi))
    info = dict(cx=cx / W * 100, cy=cy / H * 100, r_px=r_eq, npix=sz, sath=sath,
                shift=(cx / W * 100 - ex, cy / H * 100 - ey))
    return mask, info

def fit_iris_circle(bg2, cx, cy, r_hint, satmin=0.10, hue_ref=None):
    """对 (cx,cy) 附近彩色像素做最小二乘圆拟合（Kasa+IRLS 剔离群），返回整圆填充蒙版与拟合参数"""
    H, W = bg2.shape[:2]
    mx = bg2.max(axis=2); mn = bg2.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    win_r = r_hint * 2.1
    x0, x1 = int(cx/100*W - win_r/100*W), int(cx/100*W + win_r/100*W)
    y0, y1 = int(cy/100*H - win_r/100*W), int(cy/100*H + win_r/100*W)
    x0c, y0c, x1c, y1c = max(0,x0), max(0,y0), min(W,x1), min(H,y1)
    win = np.zeros((H, W), bool); win[y0c:y1c, x0c:x1c] = True
    m = (sat > satmin) & (mx > 0.08) & win
    if m.sum() < 30:
        return None, None
    if hue_ref is not None:
        r_, g_, b_ = bg2[...,0], bg2[...,1], bg2[...,2]
        hue = np.arctan2(np.sqrt(3.0)*(g_-b_), 2*r_-g_-b_)
        core = win & (sat > max(satmin, 0.18))
        if core.sum() > 30:
            hp = hue[core]
            med = np.arctan2(np.sin(hp).mean(), np.cos(hp).mean())
            dh = np.abs((hue - med + np.pi) % (2*np.pi) - np.pi)
            m = m & (dh <= np.radians(75))
    # 描边：只用彩色区域的边界像素拟合（Kasa 对实心圆盘有 r≈0.71R 偏差）
    edge = m & ~ndimage.binary_erosion(m, iterations=2)
    if edge.sum() >= 30:
        ys, xs = np.where(edge)
    else:
        ys, xs = np.where(m)
    cx0f, cy0f = cx/100*W, cy/100*H
    for _ in range(4):
        A = np.stack([xs, ys, np.ones_like(xs)], 1).astype(float)
        b = (xs.astype(float)**2 + ys.astype(float)**2)
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        a, b2, c = sol
        fx, fy = a/2, b2/2
        fr = np.sqrt(max(c + fx*fx + fy*fy, 1.0))
        d = np.abs(np.hypot(xs-fx, ys-fy) - fr)
        keep = d < max(fr*0.30, 3.0)
        if keep.sum() < 30 or keep.all():
            break
        xs, ys = xs[keep], ys[keep]
    # 护栏：半径/中心离谱则退回种子盘
    if not (0.5*r_hint/100*W <= fr <= 1.8*r_hint/100*W and np.hypot(fx-cx0f, fy-cy0f) < 0.018*W):
        return None, None
    yy, xx = np.mgrid[0:H, 0:W]
    mask = ((xx-fx)**2 + (yy-fy)**2) <= (fr*1.04)**2
    info = dict(cx=fx/W*100, cy=fy/H*100, r_pctW=fr/W*100, r_pctH=fr/H*100,
                npix=int(m.sum()), npix_fit=int(len(xs)))
    return mask, info

def bake_from_masks(bg2, masks, feather=1.4, uniform=False, colors=None):
    """uniform=True: 每眼统一用亮部颜色（暗区同亮，修"半边不闪/环形偏移"视觉病）"""
    H, W = bg2.shape[:2]
    gate = np.zeros((H, W), bool)
    for m in masks:
        if m is not None:
            gate |= m
    gate = ndimage.binary_closing(gate, structure=np.ones((5, 5)))
    alpha = ndimage.gaussian_filter(gate.astype(float), feather)
    alpha = np.clip(alpha * 1.4, 0, 1)
    if uniform:
        colorfield = np.zeros((H, W, 3))
        for i_m, m in enumerate(masks):
            if m is None or m.sum() < 10:
                continue
            if colors and i_m < len(colors) and colors[i_m] is not None:
                col = np.clip(np.array(colors[i_m]) * 1.45, 0, 1)
            else:
                px = bg2[m]
                lum = px.max(axis=1)
                bright = px[lum >= np.quantile(lum, 0.6)]
                col = np.clip(bright.mean(axis=0) * 1.45, 0, 1)
            colorfield[ndimage.binary_dilation(m, iterations=3)] = col
        rgb = colorfield * alpha[..., None]
    else:
        rgb = np.clip(bg2 * 1.35, 0, 1) * alpha[..., None]
    return (np.dstack([rgb, alpha[..., None]]) * 255).astype(np.uint8), gate

def panel(img_bg, mask, box, title):
    """bg2 裁剪 | 叠加(绿) | 烤片, 横排"""
    x0, y0, x1, y1 = box
    crop = (img_bg[y0:y1, x0:x1] * 255).astype(np.uint8).copy()
    h, w = crop.shape[:2]
    S = 300 / max(h, w)
    crop = np.asarray(Image.fromarray(crop).resize((int(w * S), int(h * S)))).astype(int)
    ov = crop.copy()
    if mask is not None:
        mm = mask[y0:y1, x0:x1]
        mi = np.asarray(Image.fromarray((mm * 255).astype(np.uint8)).resize((crop.shape[1], crop.shape[0]))).astype(float) / 255
        ov[..., 1] = np.maximum(ov[..., 1], (mi * 255).astype(int))
        ov[..., 0] = (ov[..., 0] * (1 - mi * 0.5)).astype(int)
    alone = np.zeros_like(crop)
    if mask is not None:
        m4 = mask[y0:y1, x0:x1]
        mi = np.asarray(Image.fromarray((m4 * 255).astype(np.uint8)).resize((crop.shape[1], crop.shape[0]))).astype(float) / 255
        alone = (crop * (0.25 + mi[..., None] * 1.6)).clip(0, 255).astype(int)
    row = np.concatenate([crop, ov, alone], axis=1)
    im = Image.fromarray(row.astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.text((4, 4), title, fill=(255, 80, 80))
    return im

_OVR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "circle_overrides.json")
CIRCLES = json.load(open(_OVR, encoding="utf-8")) if os.path.exists(_OVR) else {}
# nn -> {"A": [cx,cy,r_pctW,satmin,(hue)], "B": [...]/None}; 命中则该眼用圆盘门限

def _recycle_tex(P):
    tex = os.path.join(P, "materials", "eyeglow.tex")
    if os.path.exists(tex):
        lst = os.path.join(TEMP, "pupilfix", "recycle_auto.txt")
        open(lst, "w", encoding="utf-8").write(tex)
        import subprocess
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(TEMP, "recycle.ps1"), lst], capture_output=True)
        return True
    return False

def process(nn, manual=None, force_two=False):
    """manual: dict bx/by 覆盖（塌缩项目人工第二眼）"""
    d = dirs_of(nn)
    P = os.path.join(BASE, d)
    res = json.load(open(os.path.join(RESULTS, "%d.json" % int(nn)), encoding="utf-8"))
    bg2 = np.asarray(Image.open(os.path.join(P, "materials", "bg2.png")).convert("RGB")).astype(float) / 255
    H, W = bg2.shape[:2]
    ax, ay, bx, by = res["ax"], res["ay"], res["bx"], res["by"]
    collapsed = abs(ax - bx) < 0.3 and abs(ay - by) < 0.3
    if manual:
        bx, by = manual["bx"], manual["by"]
        collapsed = False
    r_px = res["r_pct"] / 100 * H

    _recycle_tex(P)
    ov = CIRCLES.get(nn, {})
    # TRACE 蒙版优先：trace_masks/NN.png 是用户描线映射到原生画布的最终蒙版
    _tm = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trace_masks", "%s_mask.png" % nn)
    if os.path.exists(_tm):
        import numpy as _np
        _m = _np.asarray(Image.open(_tm).convert("L")) > 128
        mA = _m
        mB = None
        iA = dict(cx=float(0), cy=float(0), r_px=1, npix=int(_m.sum()), sath=0, shift=(0, 0))
        iB = "traced-single-mask"
        # 质心与 A/B 拆分
        _lab, _n = ndimage.label(_m)
        _comps = []
        for _k in range(1, _n+1):
            _s = _lab == _k
            _sz = int(_s.sum())
            if _sz >= 300:
                _cy, _cx = ndimage.center_of_mass(_s)
                _comps.append((_cx/W*100, _cy/H*100, _sz))
        _comps.sort()
        if len(_comps) >= 2:
            ax, ay = _comps[0][0], _comps[0][1]
            bx, by = _comps[1][0], _comps[1][1]
        elif _comps:
            ax, ay = _comps[0][0], _comps[0][1]
            bx, by = ax, ay
    else:
        ov = ov
    def circle_mask(cx_, cy_, r_, satmin, use_hue=False):
        yy, xx = np.mgrid[0:H, 0:W]
        mxg = bg2.max(axis=2); mng = bg2.min(axis=2)
        satg = (mxg - mng) / np.maximum(mxg, 1e-6)
        disc = ((xx - cx_/100*W)**2 + (yy - cy_/100*H)**2) < (r_/100*W)**2
        m = disc & (satg > satmin) & (mxg > satmin*0.6)
        if use_hue:
            r_, g_, b_ = bg2[...,0], bg2[...,1], bg2[...,2]
            hue = np.arctan2(np.sqrt(3.0)*(g_-b_), 2*r_-g_-b_)
            core = disc & (satg > max(satmin, 0.15))
            if core.sum() > 30:
                hp = hue[core]
                med = np.arctan2(np.sin(hp).mean(), np.cos(hp).mean())
                dh = np.abs((hue - med + np.pi) % (2*np.pi) - np.pi)
                m = m & (dh <= np.radians(75))
        return m
    if "A" in ov and ov["A"][0] == "PURE":
        _, cx_, cy_, r_ = ov["A"][:4]
        yy, xx = np.mgrid[0:H, 0:W]
        mA = ((xx-cx_/100*W)**2 + (yy-cy_/100*H)**2) < (r_/100*W)**2
        iA = dict(cx=cx_, cy=cy_, r_px=r_/100*W, npix=int(mA.sum()), sath=0, shift=(0,0))
    elif "A" in ov and ov["A"][0] == "DARK":
        _, cx_, cy_, r_, vmax = ov["A"][:5]
        yy, xx = np.mgrid[0:H, 0:W]
        disc = ((xx-cx_/100*W)**2 + (yy-cy_/100*H)**2) < (r_/100*W)**2
        mA = disc & (bg2.max(axis=2) < vmax)
        iA = dict(cx=cx_, cy=cy_, r_px=r_/100*W, npix=int(mA.sum()), sath=vmax, shift=(0,0))
    elif "A" in ov and ov["A"][0] == "FIT":
        _, cx_, cy_, r_ = ov["A"][:4]
        mA, fi = fit_iris_circle(bg2, cx_, cy_, r_, satmin=ov["A"][4] if len(ov["A"])>4 else 0.10)
        if mA is None:
            mA, iA = circle_mask(cx_, cy_, r_, 0.10), dict(cx=cx_, cy=cy_, r_px=r_/100*W, npix=0, sath=0.1, shift=(0,0))
        else:
            ax, ay = fi["cx"], fi["cy"]
            r_pct_res = fi["r_pctH"]
            iA = dict(cx=fi["cx"], cy=fi["cy"], r_px=fi["r_pctW"]/100*W, npix=fi["npix"], sath=0.0,
                      shift=(fi["cx"]-cx_, fi["cy"]-cy_), fit=fi)
    elif "A" in ov:
        cx_, cy_, r_, smin = ov["A"][:4]
        mA = circle_mask(cx_, cy_, r_, smin, use_hue=(len(ov["A"]) > 4))
        iA = dict(cx=cx_, cy=cy_, r_px=r_/100*W, npix=int(mA.sum()), sath=smin, shift=(0,0))
        ax, ay = cx_, cy_
    else:
        mA, iA = detect_iris(bg2, ax, ay, r_px)
    if "B" in ov:
        if ov["B"] is None:
            mB, iB = None, "collapsed-single"
        elif ov["B"][0] == "PURE":
            _, cx_, cy_, r_ = ov["B"][:4]
            yy, xx = np.mgrid[0:H, 0:W]
            mB = ((xx-cx_/100*W)**2 + (yy-cy_/100*H)**2) < (r_/100*W)**2
            iB = dict(cx=cx_, cy=cy_, r_px=r_/100*W, npix=int(mB.sum()), sath=0, shift=(0,0))
        elif ov["B"][0] == "DARK":
            _, cx_, cy_, r_, vmax = ov["B"][:5]
            yy, xx = np.mgrid[0:H, 0:W]
            disc = ((xx-cx_/100*W)**2 + (yy-cy_/100*H)**2) < (r_/100*W)**2
            mB = disc & (bg2.max(axis=2) < vmax)
            iB = dict(cx=cx_, cy=cy_, r_px=r_/100*W, npix=int(mB.sum()), sath=vmax, shift=(0,0))
        elif ov["B"][0] == "FIT":
            _, cx_, cy_, r_ = ov["B"][:4]
            mB, fi = fit_iris_circle(bg2, cx_, cy_, r_, satmin=ov["B"][4] if len(ov["B"])>4 else 0.10)
            if mB is None:
                mB = circle_mask(cx_, cy_, r_, 0.10); iB = dict(cx=cx_, cy=cy_, r_px=r_/100*W, npix=0, sath=0.1, shift=(0,0))
            else:
                bx, by = fi["cx"], fi["cy"]
                iB = dict(cx=fi["cx"], cy=fi["cy"], r_px=fi["r_pctW"]/100*W, npix=fi["npix"], sath=0.0,
                          shift=(fi["cx"]-cx_, fi["cy"]-cy_), fit=fi)
        else:
            cx_, cy_, r_, smin = ov["B"][:4]
            mB = circle_mask(cx_, cy_, r_, smin, use_hue=(len(ov["B"]) > 4))
            iB = dict(cx=cx_, cy=cy_, r_px=r_/100*W, npix=int(mB.sum()), sath=smin, shift=(0,0))
            bx, by = cx_, cy_
    else:
        mB, iB = (None, "collapsed-single") if (collapsed and not manual) else detect_iris(bg2, bx, by, r_px)

    rgba, gate = bake_from_masks(bg2, [mA, mB], uniform=bool(ov.get("uniform")),
                                 colors=[ov.get("colA"), ov.get("colB")])
    Image.fromarray(rgba).save(os.path.join(P, "materials", "eyeglow.png"))

    # 更新坐标（有检测才精化；塌缩不动）
    nA = "A" if mA is not None else "A-MISS"
    if mA is not None:
        res["ax"], res["ay"] = round(iA["cx"], 2), round(iA["cy"], 2)
        if "A" in ov: res["r_pct"] = round(iA["r_px"] / H * 100, 2)
        if collapsed and not manual:
            res["bx"], res["by"] = res["ax"], res["ay"]
    if mB is not None:
        res["bx"], res["by"] = round(iB["cx"], 2), round(iB["cy"], 2)
        if "B" in ov and ov["B"]: res["r_pct"] = round(iB["r_px"] / H * 100, 2)
    res["notes"] = res.get("notes", "") + "; v41c rebake A%s%s B%s%s" % (
        "" if mA is not None else "=MISS",
        ("(%.1f,%.1f)" % (iA["shift"][0], iA["shift"][1])) if mA is not None else "",
        "" if mB is not None else ("=MISS" if not collapsed else "=single"),
        ("(%.1f,%.1f)" % (iB["shift"][0], iB["shift"][1])) if mB is not None else "")
    json.dump(res, open(os.path.join(RESULTS, "%d.json" % int(nn)), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 调 v41b 完成 POT/frag/材质/顺序
    import apply_v41b
    try:
        msg = apply_v41b.apply_project(d)
    except AssertionError as e:
        msg = "APPLY-ASSERT: %s" % e

    # QC 图
    half = int(W * 0.035)
    def box(ex, ey):
        cx0, cy0 = int(ex / 100 * W), int(ey / 100 * H)
        return (max(0, cx0 - half), max(0, cy0 - half), min(W, cx0 + half), min(H, cy0 + half))
    def gloss(box_):
        x0, y0, x1, y1 = box_
        g = rgba[y0:y1, x0:x1]
        a = g[..., 3:4] / 255.0
        return ((g[..., :3] * 1.2 + 40) * (0.2 + a * 1.5)).clip(0, 255)
    rows = []
    bA = box(ax, ay)
    pa = panel(bg2, mA, bA, "%s EYE-A %s npix=%s shift=%s" % (nn, nA,
               iA["npix"] if mA is not None else "-",
               "(%.1f,%.1f)" % (iA["shift"][0], iA["shift"][1]) if mA is not None else "-"))
    rows.append(np.asarray(pa))
    if not (collapsed and not manual):
        bB = box(bx, by)
        pb = panel(bg2, mB, bB, "%s EYE-B %s npix=%s shift=%s" % (nn, "B" if mB is not None else "B-MISS",
                   iB["npix"] if mB is not None else "-",
                   ("(%.1f,%.1f)" % (iB["shift"][0], iB["shift"][1])) if mB is not None else "-"))
        rows.append(np.asarray(pb))
    wmax = max(r.shape[1] for r in rows)
    canvas = np.zeros((sum(r.shape[0] for r in rows) + 10 * (len(rows) - 1), wmax, 3), np.uint8)
    y = 0
    for r in rows:
        canvas[y:y + r.shape[0], :r.shape[1]] = r
        y += r.shape[0] + 10
    Image.fromarray(canvas).save(os.path.join(QC, "%s.png" % nn))
    return dict(nn=nn, collapsed=collapsed, A=iA if mA is not None else None,
                B=None if (collapsed and not manual) else iB, apply=str(msg))

if __name__ == "__main__":
    nns = []
    for a in sys.argv[1:]:
        if a != "--qc":
            nns.extend(a.split(","))
    for nn in nns:
        r = process(nn)
        print(nn, "collapsed" if r["collapsed"] else "",
              "A:", ("ok %.2f,%.2f %dpx" % (r["A"]["cx"], r["A"]["cy"], r["A"]["npix"])) if (r["A"] and not isinstance(r["A"], str)) else str(r["A"]),
              "B:", ("ok %.2f,%.2f %dpx" % (r["B"]["cx"], r["B"]["cy"], r["B"]["npix"])) if (r["B"] and not isinstance(r["B"], str)) else ("single" if r["collapsed"] else str(r["B"])),
              "|", r["apply"][:80])
