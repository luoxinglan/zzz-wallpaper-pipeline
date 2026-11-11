# -*- coding: utf-8 -*-
"""更新影画: wiki channel 43 agents -> 意向影画 tabs -> download missing into 意向影画\原图.

Usage: python mindscapes_fill.py dry|download  (default dry)
Naming: {wiki词条名} ({N}).png matching the existing 原图 convention.
Files already present (any case/N) are never re-downloaded. New downloads are
recorded in state/mindscapes_new.json; AI 增强 (upscale_mindscapes.py in
壁纸更新工具) is a separate step and is naturally incremental.
WE 壁纸制作 itself happens in the dedicated WE conversation — this pipeline
stops at 原图/AI增强.
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hoyo_common import (ROOT_ZZZ, direct_session, dl, ext_of, fetch_page,
                         fetch_tree, load_state, mapdesc_items, sanitize,
                         save_state)

DEST = os.path.join(ROOT_ZZZ, "意向影画", "原图")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    S = direct_session()
    agents = fetch_tree(S, 43)
    print(f"channel 43: {len(agents)} agents")
    new_files = []
    missing_agents = 0
    for pid, title in agents:
        page = fetch_page(S, pid)
        want = []
        for grp, tab, url in mapdesc_items(page):
            m = re.fullmatch(r"影画展示(\d+)", (tab or "").strip())
            # wiki group is 意像影画 (0x8C61 像, NOT 意向影画 0x5411 向 — the
            # library folder spelling); empty grp occurs on fresh/collab pages
            if m and grp in ("意像影画", "意向影画", ""):
                want.append((int(m.group(1)), url))
        if not want:
            continue
        prefix = sanitize(title)
        have = set()
        if os.path.isdir(DEST):
            for fn in os.listdir(DEST):  # glob breaks on 「」· chars — iterdir+prefix
                m = re.fullmatch(re.escape(prefix) + r" \((\d+)\)\.\w+", fn)
                if m:
                    have.add(int(m.group(1)))
        todo = sorted((n, u) for n, u in want if n not in have)
        if todo:
            missing_agents += 1
            print(f"{title}: 缺 {[n for n, _ in todo]} / 共 {len(want)}")
        for n, u in todo:
            dest = os.path.join(DEST, f"{prefix} ({n}).{ext_of(u)}")
            if mode == "download":
                dl(S, u, dest)
                new_files.append(dest)
                print("  +", os.path.basename(dest))
                time.sleep(0.15)
            else:
                print("  dry +", os.path.basename(dest))
    if mode == "download":
        save_state("mindscapes_new.json", new_files)
    print(f"缺图词条 {missing_agents}，新增 {len(new_files) if mode == 'download' else 0}（dry 未下载）")


if __name__ == "__main__":
    main()
