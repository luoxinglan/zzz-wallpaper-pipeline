# -*- coding: utf-8 -*-
"""更新视频: wiki channels 73(角色视频) / 72(游戏视频) -> entry page post_id ->
getPostFull vod_list highest resolution -> 视频\{角色视频|游戏视频}\{subject}.mp4.

Usage: python wiki_videos.py dry|download  (default dry)
Signed vod URLs (prod-vod-sign, auth_key expiry) must be downloaded immediately
after the detail fetch. State state/wiki_videos_state.json {"posts": {pid:
{"title","v"}}, "entry_map": {wiki_pid: post_id}} — v:1 downloaded, v:0 post has
no vod (never re-probed); entry_map caches wiki-entry -> post_id so reruns only
fetch entry pages for new entries.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hoyo_common import (ROOT_ZZZ, direct_session, dl, fetch_page, fetch_tree,
                         load_state, post_detail, sanitize, save_state)

CHANNELS = {73: "角色视频", 72: "游戏视频"}
STATE = "wiki_videos_state.json"


def best_vod_url(vod):
    """Pick the highest resolution from one vod_list entry."""
    resolutions = vod.get("resolutions") or []

    def key(r):
        return (r.get("width") or 0, r.get("size") or 0, r.get("height") or 0)

    if not resolutions:
        return None
    return max(resolutions, key=key).get("url")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    S = direct_session()
    state = load_state(STATE, {"posts": {}, "entry_map": {}})
    seen = state["posts"]
    emap = state.setdefault("entry_map", {})
    total_new = 0
    for cid, sub in CHANNELS.items():
        entries = fetch_tree(S, cid)
        print(f"channel {cid} ({sub}): {len(entries)} entries")
        dest_dir = os.path.join(ROOT_ZZZ, "视频", sub)
        for pid, title in entries:
            if str(pid) not in emap:
                page = fetch_page(S, pid)
                blob = json.dumps(page, ensure_ascii=False)
                m = re.search(r'"post_id"\s*:\s*\\?"(\d{6,})', blob)
                emap[str(pid)] = m.group(1) if m else ""
                save_state(STATE, state)
            post_id = emap[str(pid)]
            if not post_id:
                continue  # entry without a linked bbs video post
            if post_id in seen:
                continue
            pdata = post_detail(S, post_id)  # signed URLs expire: use at once
            subject = ((pdata.get("post") or {}).get("subject")) or title
            vod_list = pdata.get("vod_list") or []
            url = best_vod_url(vod_list[0]) if vod_list else None
            if not url:
                print(f"[{sub}] {title}: post {post_id} 无 vod_list，记 v=0")
                seen[post_id] = {"title": title, "v": 0}
                save_state(STATE, state)
                continue
            dest = os.path.join(dest_dir, sanitize(subject) + ".mp4")
            print(f"[{sub}] {title} -> {os.path.basename(dest)}")
            if mode == "download":
                dl(S, url, dest)
                time.sleep(1.0)
            seen[post_id] = {"title": title, "v": 1}
            save_state(STATE, state)
            total_new += 1
    print(f"完成：新增 {total_new if mode == 'download' else 0}（dry 未下载）")


if __name__ == "__main__":
    main()
