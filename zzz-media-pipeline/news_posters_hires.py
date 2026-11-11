# -*- coding: utf-8 -*-
"""更新海报: 官网 ch278新闻/279公告/280活动 -> per-post sContent big images
(width>=1200px, ratio 1/3.2~3.2) -> 新闻海报\\{新闻|公告|活动}\\.

Usage: python news_posters_hires.py dry|download  (default dry)
- 3 download threads, direct connection (bypass Clash), resumable state
  state/news_hires_state.json {"<iInfoId>": {"stem","n","ch"}}.
- stem = YYYYMMDD-{sTitle}; first image plain stem.ext, later stem(k).ext.
- on success any old 940x529 banner sharing the stem is sent to the recycle bin.
- full backfill is ~1600 posts / several hours; incremental runs are minutes.
"""
import io
import os
import re
import sys
import threading
import time
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hoyo_common import (ROOT_ZZZ, ZZZ_CN_APP, direct_session, get_recycle,
                         load_state, save_state, sanitize)

from PIL import Image

CHANNELS = {278: "新闻", 279: "公告", 280: "活动"}
STATE = "news_hires_state.json"
MIN_W = 1200
RATIO_LO, RATIO_HI = 1 / 3.2, 3.2
OLD_BANNER = (940, 529)

_state_lock = threading.Lock()


def list_items(S, chan):
    out, page = [], 1
    while True:
        j = S.get(f"{ZZZ_CN_APP}/getContentList",
                  params={"iChanId": chan, "iPageSize": 50, "iPage": page,
                          "sLangKey": "zh-cn"}, timeout=60).json()
        d = j.get("data") or {}
        lst = d.get("list") or []
        if not lst:
            break
        out += lst
        if page * 50 >= (d.get("iTotal") or 0):
            break
        page += 1
        time.sleep(0.1)
    return out


def process(S, recycle, item, chan_id, chan_name, state, mode):
    iid = str(item["iInfoId"])
    if iid in state:
        return
    title = item.get("sTitle") or ""
    date = (item.get("dtCreateTime") or "")[:10].replace("-", "")
    stem = f"{date}-{sanitize(title)}" if date else sanitize(title)
    content = item.get("sContent") or ""
    srcs = re.findall(r'<img[^>]+src="([^"]+)"', content)
    dest_dir = os.path.join(ROOT_ZZZ, "新闻海报", chan_name)
    saved = 0
    for u in srcs:
        try:
            r = S.get(u, timeout=(20, 120))
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content))
            w, h = im.size
        except Exception:
            continue
        if w < MIN_W or not (RATIO_LO <= w / h <= RATIO_HI):
            continue
        ext = "png" if im.format == "PNG" else "jpg"
        saved += 1
        name = f"{stem}.{ext}" if saved == 1 else f"{stem}({saved}).{ext}"
        if mode == "download":
            dest = os.path.join(dest_dir, name)
            with open(dest, "wb") as f:
                f.write(r.content)
            # replace legacy 940x529 banner for the same stem
            for fn in os.listdir(dest_dir):
                if fn.startswith(stem) and fn != name:
                    p = os.path.join(dest_dir, fn)
                    try:
                        if Image.open(p).size == OLD_BANNER:
                            recycle(p)
                            print("  回收旧banner:", fn)
                    except Exception:
                        pass
    if mode == "download":
        with _state_lock:
            state[iid] = {"stem": stem, "n": saved, "ch": str(chan_id)}
            save_state(STATE, state)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    S = direct_session()
    recycle = get_recycle()
    state = load_state(STATE, {})
    todo_all = 0
    for chan_id, chan_name in CHANNELS.items():
        items = list_items(S, chan_id)
        pending = [it for it in items if str(it["iInfoId"]) not in state]
        todo_all += len(pending)
        print(f"ch{chan_id} {chan_name}: {len(items)} 帖, 待处理 {len(pending)}")
        if mode == "dry":
            for it in pending[:5]:
                date = (it.get("dtCreateTime") or "")[:10].replace("-", "")
                print("  dry:", f"{date}-{sanitize(it.get('sTitle') or '')}")
            continue
        with cf.ThreadPoolExecutor(max_workers=3) as ex:
            futs = [ex.submit(process, S, recycle, it, chan_id, chan_name, state, mode)
                    for it in pending]
            for i, f in enumerate(cf.as_completed(futs), 1):
                f.result()
                if i % 25 == 0:
                    print(f"  进度 {i}/{len(pending)}", flush=True)
    print(f"待处理总计 {todo_all}，{'已全部处理' if mode == 'download' else 'dry 未处理'}")


if __name__ == "__main__":
    main()
