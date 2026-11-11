# -*- coding: utf-8 -*-
"""Detect colored eye accents on bg2 (grayscale character + colored eyes).

Uses current results as prior; snaps A/B to the nearest saturated cluster.
Falls back to prior values when bg2 has no usable color accent (e.g. pure B/W).
"""
import os, json, math
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"

def clusters(img, sat_thr=0.32, val_thr=0.12):
    H, W = img.shape[:2]
    mx = img.max(2); mn = img.min(2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    mask = (sat > sat_thr) & (mx > val_thr)
    mask = ndimage.binary_opening(mask, np.ones((3, 3)))
    lab, n = ndimage.label(mask)
    out = []
    for i in range(1, n + 1):
        m = lab == i
        a = int(m.sum())
        if a < 40:
            continue
        d = 2 * math.sqrt(a / math.pi)
        if d < 0.004 * W or d > 0.11 * W:
            continue
        cy, cx = ndimage.center_of_mass(m)
        ys, xs = np.where(m)
        w = xs.max() - xs.min() + 1; h = ys.max() - ys.min() + 1
        r = w / max(1.0, h)
        if r > 4.5 or r < 0.22:
            continue
        vals = mx[m]
        bright = img[m][vals >= np.percentile(vals, 60)]
        col = bright.mean(0) if len(bright) else img[m].mean(0)
        out.append(dict(x=cx / W * 100, y=cy / H * 100, d=d, w=w, h=h,
                        hex='#%02X%02X%02X' % tuple(int(c * 255) for c in col),
                        area=a))
    return out

def main():
    rows = []
    for f in sorted(os.listdir(RES)):
        if not f.endswith('.json'):
            continue
        res = json.load(open(os.path.join(RES, f), encoding='utf-8'))
        nn = res['nn']
        if nn == 26:
            rows.append((nn, 'off(闭眼)')); continue
        pref = 'zzz_mindscape_%02d_' % nn
        pd = [x for x in os.listdir(BASE) if x.startswith(pref)][0]
        img = np.asarray(Image.open(os.path.join(BASE, pd, 'materials', 'bg2.png')).convert('RGB'), dtype=float) / 255
        H, W = img.shape[:2]
        cs = clusters(img)
        single = res['color_b'].upper() == '#000000'
        pick = {}
        for tag, (px, py) in (('A', (res['ax'], res['ay'])), ('B', (res['bx'], res['by']))):
            best = None
            for c in cs:
                dist = math.hypot(c['x'] - px, c['y'] - py * W / H * 0 + (c['y'] - py) * H / W)  # px in %W units approx
                dist = math.hypot((c['x'] - px) * W, (c['y'] - py) * H) / W  # %W true distance
                if dist <= 6.0 and (best is None or dist < best[0]):
                    best = (dist, c)
            if best:
                pick[tag] = best[1]
        if 'A' in pick and 'B' in pick and pick['A'] is pick['B']:
            # same blob: keep single
            del pick['B']
        if not pick:
            rows.append((nn, 'no-accent->keep')); continue
        if 'A' not in pick: pick['A'] = pick['B']
        if 'B' not in pick and not single: pass
        newA = pick['A']; newB = pick.get('B')
        dA = math.hypot((newA['x'] - res['ax']) * W, (newA['y'] - res['ay']) * H) / W
        msg = 'A(%g,%g)->(%.1f,%.1f)' % (res['ax'], res['ay'], newA['x'], newA['y']) if dA > 0.05 else 'A~'
        if newB is not None:
            dB = math.hypot((newB['x'] - res['bx']) * W, (newB['y'] - res['by']) * H) / W
            msg += ' B(%g,%g)->(%.1f,%.1f)' % (res['bx'], res['by'], newB['x'], newB['y']) if dB > 0.05 else ' B~'
        else:
            msg += ' B:none'
        r1 = newA['d'] / 2 / H * 100 * 0.9
        r2 = newB['d'] / 2 / H * 100 * 0.9 if newB else None
        rr = round(min(5.5, max(0.6, (r1 + r2) / 2 if r2 else r1)), 2)
        res['ax'], res['ay'] = round(newA['x'], 2), round(newA['y'], 2)
        if newB is not None:
            res['bx'], res['by'] = round(newB['x'], 2), round(newB['y'], 2)
        else:
            res['bx'], res['by'] = res['ax'], res['ay']
            res['color_b'] = '#000000'
        res['r_pct'] = rr
        res['color_a'] = newA['hex'].upper()
        if newB is not None:
            res['color_b'] = newB['hex'].upper()
        res['notes'] = res.get('notes', '') + '; v36 bg2色斑定位'
        json.dump(res, open(os.path.join(RES, f), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        rows.append((nn, msg + ' r=%s colA=%s' % (rr, res['color_a'])))
        print('%02d %s' % (nn, rows[-1][1]))
    return rows

if __name__ == '__main__':
    main()
