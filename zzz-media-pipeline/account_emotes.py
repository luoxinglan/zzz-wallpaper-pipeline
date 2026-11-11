# -*- coding: utf-8 -*-
"""更新表情包/头像: miyoushe official account (uid=152039148) posts filtered by
keyword -> post images + minas full-size packs -> 表情包\\ / 官方头像\\.

Usage: python account_emotes.py dry|download [--kw 表情包,头像]  (default dry)
- kw selects post-subject keywords; default covers both 表情包 and 头像 posts.
- dest by keyword: 头像 posts -> 官方头像\\, everything else -> 表情包\\.
- naming: {subject}-{n:02d}.{ext}; minas pack files {subject}-包-{origname}
  (minas pack wins: full size, single source).
- skip images < 30KB and QR-code-size junk. Emote rules (png only, 单一来源,
  命名体现系列名, 不收组合长图) are enforced at merge/review time.
- minas password regex MUST stay narrow (\\S+ swallows HTML and loses packs).
State: state/account_posts_state.json {"posts": {pid: {"subject","kw","imgs"}}}.
"""
import io
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hoyo_common import (ROOT_ZZZ, Minas, MINAS_LINK_RE, MINAS_PWD_RE,
                         direct_session, iter_posts, load_state, post_detail,
                         sanitize, save_state)

from PIL import Image

STATE = "account_posts_state.json"
UID = "152039148"
DEFAULT_KW = ("表情包", "头像")
MIN_BYTES = 30 * 1024
EXCLUDE_SUBSTR = ("二维码",)  # quick junk filter; size filter does the rest


def kw_of(subject, kws):
    for kw in kws:
        if kw in subject:
            return kw
    return None


def dest_dir_for(kw):
    return os.path.join(ROOT_ZZZ, "官方头像" if "头像" in kw else "表情包")


def save_post_images(S, subject_s, urls, dest_dir, mode):
    saved = 0
    for i, u in enumerate(urls, 1):
        try:
            r = S.get(u, timeout=(20, 120))
            r.raise_for_status()
            data = r.content
        except Exception:
            continue
        if len(data) < MIN_BYTES or any(x in u for x in EXCLUDE_SUBSTR):
            continue
        ext = "png"
        try:
            fmt = Image.open(io.BytesIO(data)).format
            ext = {"PNG": "png", "JPEG": "jpg", "GIF": "gif", "WEBP": "webp"}.get(fmt, "png")
        except Exception:
            pass
        saved += 1
        dest = os.path.join(dest_dir, f"{subject_s}-{saved:02d}.{ext}")
        if mode == "download":
            with open(dest, "wb") as f:
                f.write(data)
            print("  +", os.path.basename(dest))
    return saved


def save_minas_pack(S, subject_s, token, pwd, dest_dir, mode):
    minas = Minas()
    names = list(minas.walk(token, pwd))
    print(f"  minas包: {len(names)} 个文件")
    n = 0
    for fp in names:
        name = os.path.basename(fp)
        if not re.search(r"\.(jpe?g|png|webp|gif)$", name, re.I):
            continue
        n += 1
        dest = os.path.join(dest_dir, f"{subject_s}-包-{sanitize(name)}")
        if mode != "download":
            continue
        data = minas.download(token, pwd, fp)
        if not data:
            print("  minas 下载失败:", name)
            continue
        with open(dest, "wb") as f:
            f.write(data)
        time.sleep(0.12)
    return n


def main():
    argv = sys.argv[1:]
    mode = argv[0] if argv else "dry"
    kws = DEFAULT_KW
    if "--kw" in argv:
        kws = tuple(argv[argv.index("--kw") + 1].split(","))
    S = direct_session()
    state = load_state(STATE, {"posts": {}})
    seen = state["posts"]
    n_new_posts = 0
    for it in iter_posts(S, uid=UID):
        p = it.get("post") or {}
        pid = str(p.get("post_id") or "")
        subject = p.get("subject") or ""
        kw = kw_of(subject, kws)
        if not pid or not kw:
            continue
        if pid in seen:
            continue
        print(f"[{kw}] {subject}")
        pdata = post_detail(S, pid)
        inner = pdata.get("post") or {}
        content = inner.get("content") or ""
        dest_dir = dest_dir_for(kw)
        n_img = 0
        if mode == "download":
            urls = [x.get("url") for x in (it.get("image_list") or []) if x.get("url")]
            n_img = save_post_images(S, sanitize(subject), urls, dest_dir, mode)
        # minas pack (priority source)
        mt = MINAS_LINK_RE.search(content)
        mp = MINAS_PWD_RE.search(content)
        if mt and mp:
            token, pwd = mt.group(1), mp.group(1)
            n_img += save_minas_pack(S, sanitize(subject), token, pwd, dest_dir, mode)
        elif mode == "download":
            print("  (无 minas 链接)")
        seen[pid] = {"subject": subject, "kw": kw, "imgs": n_img}
        save_state(STATE, state)
        n_new_posts += 1
        time.sleep(0.2)
    print(f"新帖 {n_new_posts}（dry 只列出不下载）")


if __name__ == "__main__":
    main()
