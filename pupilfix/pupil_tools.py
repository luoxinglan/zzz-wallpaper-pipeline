# -*- coding: utf-8 -*-
"""Pupil pulse alignment tooling for WE zzz_mindscape projects.

Commands (all outputs go to this script's directory):
  coarse <NN>                          -> NN_coarse.png  (1400px wide, 5% grid labeled)
  fine   <NN> <cx> <cy> <tag> [half]   -> NN_fine_<tag>.png (native-res crop around cx,cy %, 1% grid + 0.25% ticks)
  sample <NN> <ax> <ay> <bx> <by> <r_pct> -> iris color stats + NN_color.png (swatch check)
  overlay <NN> <ax> <ay> <bx> <by> <r_pct> [hex] -> NN_verify.png (glow preview over both eyes)

Coordinates are % of bg3.png (x from left, y from TOP), matching shader convention.
Radius is % of image height.
"""
import os, sys, math, colorsys, json
from PIL import Image, ImageDraw, ImageFont

BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
OUT = os.path.dirname(os.path.abspath(__file__))

def find_proj(nn):
    pref = "zzz_mindscape_%02d_" % nn
    for d in os.listdir(BASE):
        if d.startswith(pref):
            return os.path.join(BASE, d)
    raise SystemExit("project %02d not found" % nn)

def font(sz):
    for f in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()

def label(d, xy, text, sz=18, col=(255,60,60)):
    d.text(xy, text, font=font(sz), fill=(0,0,0))
    d.text((xy[0]-1, xy[1]-1), text, font=font(sz), fill=col)

def grid(im, step_px, major, x0px, y0px, W, H, minor_px=None, sz=16):
    """Draw grid over image im (a crop of the full image). step_px = % step in full-image px."""
    d = ImageDraw.Draw(im)
    # vertical lines
    xv = math.floor(x0px / step_px) * step_px
    while xv <= x0px + W + 1:
        x = xv - x0px
        if 0 <= x <= W:
            pct = xv / Wfull
            ismaj = abs(xv / step_px - round(xv / step_px)) < 1e-6 and (round(xv/step_px) % major == 0)
            d.line([(x,0),(x,im.height)], fill=(255,255,255) if ismaj else (150,150,150), width=2 if ismaj else 1)
            if ismaj: label(d, (x+3, 3), "%.0f" % (100*xv/Wfull), sz)
        xv += step_px
    yv = math.floor(y0px / step_px) * step_px
    while yv <= y0px + H + 1:
        y = yv - y0px
        if 0 <= y <= H:
            ismaj = abs(yv / step_px - round(yv/step_px)) < 1e-6 and (round(yv/step_px) % major == 0)
            d.line([(0,y),(im.width,y)], fill=(255,255,255) if ismaj else (150,150,150), width=2 if ismaj else 1)
            if ismaj: label(d, (3, y+3), "%.0f" % (100*yv/Hfull), sz, (80,255,80))
        yv += step_px
    # minor ticks every 0.25%
    if minor_px:
        d2 = ImageDraw.Draw(im)
        xv = math.floor(x0px/minor_px)*minor_px
        while xv <= x0px+W+1:
            x = xv-x0px
            if 0<=x<=W: d2.line([(x,0),(x,7)], fill=(255,120,0), width=1)
            xv += minor_px
        yv = math.floor(y0px/minor_px)*minor_px
        while yv <= y0px+H+1:
            y = yv-y0px
            if 0<=y<=H: d2.line([(0,y),(7,y)], fill=(255,120,0), width=1)
            yv += minor_px
    return d

Wfull = Hfull = 1  # globals set by caller

def load_bg3(nn):
    p = os.path.join(find_proj(nn), "materials", "bg3.png")
    return Image.open(p).convert("RGB")

def cmd_coarse(nn):
    global Wfull, Hfull
    im0 = load_bg3(nn)
    Wfull, Hfull = im0.size
    w = 1400
    im = im0.resize((w, round(Hfull*w/Wfull)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    step = w/20  # 5%
    for i in range(21):
        x = i*step
        d.line([(x,0),(x,im.height)], fill=(255,255,255) if i%5==0 else (160,160,160), width=2 if i%5==0 else 1)
        if i%1==0: label(d,(x+2,2),"%.0f"%(i*5),14)
    for j in range(21):
        y = j*(im.height/20)
        d.line([(0,y),(w,y)], fill=(255,255,255) if j%5==0 else (160,160,160), width=2 if j%5==0 else 1)
        label(d,(2,y+2),"%.0f"%(j*5),14,(80,255,80))
    im.save(os.path.join(OUT, "%02d_coarse.png"%nn))
    print("saved coarse %dx%d (orig %dx%d)" % (im.size[0], im.size[1], Wfull, Hfull))

def cmd_fine(nn, cx, cy, tag, half=8.0):
    global Wfull, Hfull
    im0 = load_bg3(nn)
    Wfull, Hfull = im0.size
    hx = half/100.0*Wfull; hy = half/100.0*Wfull  # square-ish in px by width
    x0 = max(0, cx/100.0*Wfull - hx); y0 = max(0, cy/100.0*Hfull - hy)
    x1 = min(Wfull, cx/100.0*Wfull + hx); y1 = min(Hfull, cy/100.0*Hfull + hy)
    im = im0.crop((round(x0), round(y0), round(x1), round(y1)))
    grid(im, Wfull/100.0, 1, x0, y0, im.width, im.height, minor_px=Wfull/400.0)
    # crosshair at requested center
    d = ImageDraw.Draw(im)
    px, py = cx/100.0*Wfull-x0, cy/100.0*Hfull-y0
    d.line([(px-25,py),(px+25,py)], fill=(0,255,255), width=2)
    d.line([(px,py-25),(px,py+25)], fill=(0,255,255), width=2)
    fn = os.path.join(OUT, "%02d_fine_%s.png" % (nn, tag))
    im.save(fn)
    print("saved %s crop=%dx%d center_px=(%.0f,%.0f) grid=1%% (%.0f px)" % (os.path.basename(fn), im.width, im.height, cx/100.0*Wfull-x0, cy/100.0*Hfull-y0, Wfull/100.0))

def eye_color(im, cpx, cpy, r_px):
    import numpy as np
    a = np.asarray(im, dtype=float)/255.0
    x0,x1 = max(0,int(cpx-r_px)), min(a.shape[1], int(cpx+r_px)+1)
    y0,y1 = max(0,int(cpy-r_px)), min(a.shape[0], int(cpy+r_px)+1)
    xs = np.arange(x0,x1); ys = np.arange(y0,y1)
    xx,yy = np.meshgrid(xs,ys)
    m = (xx-cpx)**2 + (yy-cpy)**2 <= r_px*r_px*0.81  # 0.9 radius -> slightly inside
    R = a[y0:y1,x0:x1,0][m]; G = a[y0:y1,x0:x1,1][m]; B = a[y0:y1,x0:x1,2][m]
    if len(R) < 20: return None
    mx = np.maximum(np.maximum(R,G),B); mn = np.minimum(np.minimum(R,G),B)
    V = mx; S = np.where(mx>0,(mx-mn)/np.maximum(mx,1e-6),0)
    keep = (V >= 0.12) & ~((S < 0.20) & (V > 0.72))  # drop outline & glints
    if keep.sum() < max(15, len(R)*0.08): keep = V >= 0.08  # fallback: nearly-black iris
    wgt = (S*0.55 + V*0.45)[keep]
    if wgt.sum() <= 0: wgt = np.ones(keep.sum())
    r = float((R[keep]*wgt).sum()/wgt.sum()); g = float((G[keep]*wgt).sum()/wgt.sum()); b = float((B[keep]*wgt).sum()/wgt.sum())
    return r,g,b,int(keep.sum()),int(len(R))

def fmt(r,g,b):
    return "%02X%02X%02X" % (round(r*255), round(g*255), round(b*255))

def cmd_sample(nn, ax, ay, bx, by, r_pct):
    im = load_bg3(nn); W,H = im.size
    r_px = r_pct/100.0*H
    resA = eye_color(im, ax/100.0*W, ay/100.0*H, r_px)
    resB = eye_color(im, bx/100.0*W, by/100.0*H, r_px)
    out = []
    for tag,res in (("A",resA),("B",resB)):
        if not res: print("eye %s: too few pixels"%tag); out.append(None); continue
        r,g,b,nk,nt = res
        bright = ""
        if max(r,g,b) < 0.35:
            s = 0.55/max(r,g,b); r,g,b = min(1,r*s),min(1,g*s),min(1,b*s); bright=" [brightened dark iris]"
        print("eye %s: #%s rgb(%.3f %.3f %.3f) kept %d/%d%s" % (tag, fmt(r,g,b), r,g,b, nk, nt, bright))
        out.append((r,g,b))
    # swatch check image: both eye crops side by side with color patch
    crops = []
    for (cx,cy),res in (((ax,ay),out[0]),((bx,by),out[1])):
        w = int(r_px*4.5); x0 = max(0,int(cx/100*W-w)); y0 = max(0,int(cy/100*H-w))
        crops.append(im.crop((x0,y0,min(W,x0+2*w),min(H,y0+2*w))))
    Wc = sum(c.width for c in crops)+90; Hc = max(c.height for c in crops)+60
    canvas = Image.new("RGB",(Wc,Hc),(30,30,30))
    x=0
    d=None
    for c,(r,g,b) in zip(crops,[o if o else (0.5,0.5,0.5) for o in out]):
        canvas.paste(c,(x,50))
        d = ImageDraw.Draw(canvas)
        d.rectangle([x,10,x+60,46], fill=(round(r*255),round(g*255),round(b*255)), outline=(255,255,255))
        x += c.width+30
    canvas.save(os.path.join(OUT,"%02d_color.png"%nn))
    print("saved %02d_color.png"%nn)

def cmd_overlay(nn, ax, ay, bx, by, r_pct, hexcol="FF4040"):
    im = load_bg3(nn); W,H = im.size
    r_px = r_pct/100.0*H
    r,g,b = int(hexcol[0:2],16)/255, int(hexcol[2:4],16)/255, int(hexcol[4:6],16)/255
    mx0 = min(ax,bx)-14; mx1 = max(ax,bx)+14
    my0 = min(ay,by)-12; my1 = max(ay,by)+12
    x0 = max(0,mx0/100*W); x1 = min(W,mx1/100*W)
    y0 = max(0,my0/100*H); y1 = min(H,my1/100*H)
    crop = im.crop((round(x0),round(y0),round(x1),round(y1))).convert("RGB")
    px = crop.load()
    import numpy as np
    a = np.asarray(crop,dtype=float)/255.0
    yy,xx = np.mgrid[0:crop.height,0:crop.width]
    for (cx,cy) in ((ax,ay),(bx,by)):
        gx,gy = cx/100*W-x0, cy/100*H-y0
        m2 = (xx-gx)**2+(yy-gy)**2 <= r_px*r_px
        a[m2] = np.clip(a[m2] + np.array([r,g,b])*0.75, 0, 1)
    im2 = Image.fromarray((a*255).astype('uint8'))
    d = ImageDraw.Draw(im2)
    for (cx,cy) in ((ax,ay),(bx,by)):
        gx,gy = cx/100*W-x0, cy/100*H-y0
        d.ellipse([gx-r_px,gy-r_px,gx+r_px,gy+r_px], outline=(255,255,0), width=3)
        d.line([(gx-r_px-20,gy),(gx+r_px+20,gy)], fill=(255,255,0), width=1)
        d.line([(gx,gy-r_px-20),(gx,gy+r_px+20)], fill=(255,255,0), width=1)
    if im2.width > 1800:
        im2 = im2.resize((1800, round(im2.height*1800/im2.width)), Image.LANCZOS)
    im2.save(os.path.join(OUT,"%02d_verify.png"%nn))
    print("saved %02d_verify.png radius_px=%.0f color=#%s"%(nn,r_px,hexcol))

def kasa_fit(px, py):
    """Algebraic circle fit. Returns (cx, cy, r, rms)."""
    import numpy as np
    A = np.column_stack([px, py, np.ones(len(px))])
    b = px*px + py*py
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0]/2, sol[1]/2
    r = math.sqrt(max(0.0, sol[2] + cx*cx + cy*cy))
    rms = float(np.sqrt(np.mean((np.hypot(px-cx, py-cy) - r)**2)))
    return cx, cy, r, rms

def detect_iris_blob(gray_win, seed_xy, rough_r):
    """Find dark or bright round blob near seed in a window. Returns dict or None."""
    import numpy as np
    from scipy import ndimage
    sx, sy = seed_xy
    best = None
    for polarity, thr in (("dark", np.percentile(gray_win, 22)),
                          ("bright", np.percentile(gray_win, 82))):
        mask = (gray_win < thr) if polarity == "dark" else (gray_win > thr)
        mask = ndimage.binary_opening(mask, structure=np.ones((3,3)))
        lab, n = ndimage.label(mask)
        if not n: continue
        # iterate all components properly
        for li in range(1, n+1):
            comp = lab == li
            area = int(comp.sum())
            if area < math.pi*7*7 or area > math.pi*130*130: continue
            cyw, cxw = ndimage.center_of_mass(comp)
            if math.hypot(cxw-sx, cyw-sy) > max(30.0, rough_r*1.2): continue
            filled = ndimage.binary_fill_holes(comp)
            area_f = int(filled.sum())
            ys, xs = np.where(filled)
            w = xs.max()-xs.min()+1; h = ys.max()-ys.min()+1
            roundness = min(w,h)/max(w,h)
            if roundness < 0.45: continue
            eqr = math.sqrt(area_f/math.pi)
            # boundary band for circle fit
            er = ndimage.binary_erosion(filled, iterations=max(2, int(eqr*0.25)))
            band = filled & ~er
            bys, bxs = np.where(band)
            if len(bxs) >= 12:
                cx, cy, r, rms = kasa_fit(bxs.astype(float), bys.astype(float))
            else:
                cx, cy, r, rms = cxw, cyw, eqr, -1
            score = roundness * min(1.0, eqr/max(8.0, rough_r*0.5))
            cand = {"polarity": polarity, "cx": float(cx), "cy": float(cy), "r": float(r),
                    "eqr": eqr, "round": roundness, "area": area_f, "fit_rms": rms, "score": score}
            if best is None or cand["score"] > best["score"]:
                best = cand
    return best

def cmd_refine(nn, cx, cy, tag, rough_d=2.5):
    """Numeric iris refine around seed (cx,cy %). rough_d = rough iris diameter in % of width."""
    import numpy as np
    from scipy import ndimage
    im0 = load_bg3(nn); W, H = im0.size
    g = np.asarray(im0.convert("L"), dtype=float)
    g = ndimage.gaussian_filter(g, 1.2)
    spx, spy = cx/100.0*W, cy/100.0*H
    half = max(60.0, rough_d/100.0*W*1.6)
    x0 = max(0, int(spx-half)); x1 = min(W, int(spx+half))
    y0 = max(0, int(spy-half)); y1 = min(H, int(spy+half))
    win = g[y0:y1, x0:x1]
    rough_r = rough_d/100.0*W/2
    res = detect_iris_blob(win, (spx-x0, spy-y0), rough_r)
    fn = os.path.join(OUT, "%02d_refine_%s.png" % (nn, tag))
    if res is None:
        # save window for debugging anyway
        Image.fromarray(win.astype('uint8')).save(fn)
        print("REFINE FAIL no candidate (seed %.1f,%.1f)" % (cx, cy))
        return None
    gx, gy = res["cx"]+x0, res["cy"]+y0
    rpct = res["r"]/H*100
    # debug image: native crop with fitted circle
    d2 = max(50, int(res["r"]*3.2))
    c0x, c0y = max(0, int(gx-d2)), max(0, int(gy-d2))
    crop = im0.crop((c0x, c0y, min(W, int(gx+d2)), min(H, int(gy+d2))))
    dd = ImageDraw.Draw(crop)
    dd.ellipse([gx-c0x-res["r"], gy-c0y-res["r"], gx-c0x+res["r"], gy-c0y+res["r"]], outline=(255,255,0), width=3)
    dd.line([(gx-c0x-res["r"]-15, gy-c0y), (gx-c0x+res["r"]+15, gy-c0y)], fill=(0,255,255), width=2)
    dd.line([(gx-c0x, gy-c0y-res["r"]-15), (gx-c0x, gy-c0y+res["r"]+15)], fill=(0,255,255), width=2)
    crop.save(fn)
    print("REFINE %s: center=(%.2f, %.2f) r=%.2f%%H (eqr=%.1fpx round=%.2f pol=%s rms=%.1f)" %
          (tag, gx/W*100, gy/H*100, rpct, res["eqr"], res["round"], res["polarity"], res["fit_rms"]))
    return {"ax": gx/W*100, "ay": gy/H*100, "r_pct": rpct}

def cmd_pair(nn, ax, ay, bx, by):
    """Single crop spanning both eyes with 1% grid + seed crosshairs A/B."""
    global Wfull, Hfull
    im0 = load_bg3(nn)
    Wfull, Hfull = im0.size
    mx0 = min(ax,bx)-7.5; mx1 = max(ax,bx)+7.5
    my0 = min(ay,by)-6.0; my1 = max(ay,by)+6.0
    x0 = max(0, mx0/100.0*Wfull); x1 = min(Wfull, mx1/100.0*Wfull)
    y0 = max(0, my0/100.0*Hfull); y1 = min(Hfull, my1/100.0*Hfull)
    im = im0.crop((round(x0), round(y0), round(x1), round(y1)))
    grid(im, Wfull/100.0, 1, x0, y0, im.width, im.height, minor_px=Wfull/400.0)
    d = ImageDraw.Draw(im)
    for (cx,cy),t in (((ax,ay),"A"),((bx,by),"B")):
        px, py = cx/100.0*Wfull-x0, cy/100.0*Hfull-y0
        d.line([(px-30,py),(px+30,py)], fill=(0,255,255), width=2)
        d.line([(px,py-30),(px,py+30)], fill=(0,255,255), width=2)
        label(d,(px+8,py+8),t,20,(0,255,255))
    fn = os.path.join(OUT, "%02d_pair.png" % nn)
    if im.width > 1400:
        im = im.resize((1400, round(im.height*1400/im.width)), Image.LANCZOS)
    im.save(fn)
    print("saved %s crop=%dx%d" % (os.path.basename(fn), im.width, im.height))

def cmd_write(nn, ax, ay, bx, by, r_pct, ca, cb, visible, conf, notes):
    fn = os.path.join(OUT, "results", "%d.json" % nn)
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    json.dump({"nn": nn, "eyes_visible": visible, "ax": ax, "ay": ay, "bx": bx, "by": by,
               "r_pct": r_pct, "color_a": ca, "color_b": cb, "confidence": conf, "notes": notes},
              open(fn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", fn)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "coarse": cmd_coarse(int(sys.argv[2]))
    elif cmd == "fine": cmd_fine(int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5], float(sys.argv[6]) if len(sys.argv)>6 else 8.0)
    elif cmd == "refine": cmd_refine(int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5], float(sys.argv[6]) if len(sys.argv)>6 else 2.5)
    elif cmd == "pair": cmd_pair(int(sys.argv[2]), *[float(x) for x in sys.argv[3:7]])
    elif cmd == "write": cmd_write(int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]), float(sys.argv[7]), sys.argv[8], sys.argv[9], sys.argv[10]=="true", sys.argv[11] if len(sys.argv)>11 else "high", sys.argv[12] if len(sys.argv)>12 else "")
    elif cmd == "sample": cmd_sample(int(sys.argv[2]), *[float(x) for x in sys.argv[3:8]])
    elif cmd == "overlay":
        args = sys.argv[3:]
        cmd_overlay(int(sys.argv[2]), *[float(x) for x in args[:5]] + ([args[5]] if len(args)>5 else []))
    else: print(__doc__)
