# -*- coding: utf-8 -*-
"""未归档影像米游社兜底 (mys_unarc_fill): roles whose wiki entry lacks the
未归档影像 module get them from official-account miyoushe posts.

Usage: python mys_unarc_fill.py dry|download  (default dry)
Scans official account posts with 未归档影像 in the subject, extracts the role
name (「X」 bracket, else text before 未归档影像), and downloads post images
continuing the existing {role}-未归档影像{N}.ext numbering. Known-complete
series (20 roles, 2026-10) simply have no pending posts.
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hoyo_common import (ROOT_ZZZ, OFFICIAL_UID, direct_session, iter_posts,
                         load_state, sanitize, save_state)

UNARC_DIR = os.path.join(ROOT_ZZZ, "未归档影像")
STATE = "mys_unarc_state.json"


def role_of(subject):
    m = re.search(r"「([^」]+)」", subject)
    if m:
        return m.group(1)
    m = re.match(r"《?([^《》「」]+?)\s*[-—|]?未归档影像", subject)
    if m and m.group(1).strip():
        return m.group(1).strip().strip("-—| ")
    return None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    S = direct_session()
    state = load_state(STATE, {"posts": {}})
    n_new = 0
    for it in iter_posts(S, uid=OFFICIAL_UID):
        p = it.get("post") or {}
        pid = str(p.get("post_id") or "")
        subject = p.get("subject") or ""
        if "未归档影像" not in subject or not pid or pid in state["posts"]:
            continue
        role = role_of(subject)
        print(f"post {pid}: {subject} -> role={role}")
        state["posts"][pid] = {"subject": subject, "role": role}
        if not role:
            continue
        prefix = sanitize(role)
        have = 0
        if os.path.isdir(UNARC_DIR):
            for fn in os.listdir(UNARC_DIR):
                m = re.fullmatch(re.escape(prefix) + r"-未归档影像(\d+)\.\w+", fn)
                if m:
                    have = max(have, int(m.group(1)))
        urls = [x.get("url") for x in (it.get("image_list") or []) if x.get("url")]
        for i, u in enumerate(urls, 1):
            idx = have + i
            ext_m = re.search(r"\.(\w{3,4})(?:\?|$)", u)
            ext = (ext_m.group(1).lower() if ext_m else "png").replace("jpeg", "jpg")
            dest = os.path.join(UNARC_DIR, f"{prefix}-未归档影像{idx}.{ext}")
            print(("  + " if mode == "download" else "  dry + ") + os.path.basename(dest))
            if mode == "download":
                from hoyo_common import dl
                dl(S, u, dest)
                time.sleep(0.15)
            n_new += 1
        save_state(STATE, state)
    print(f"兜底新增 {n_new if mode == 'download' else 0}（dry 未下载）")


if __name__ == "__main__":
    main()
