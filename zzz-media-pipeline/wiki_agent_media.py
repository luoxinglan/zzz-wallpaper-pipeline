# -*- coding: utf-8 -*-
"""更新代理人媒体: wiki channel 43 agents -> map_desc tab classification.

Usage: python wiki_agent_media.py dry|download  (default dry — review first!)
Collected (established 2026-10 rules):
  时装展示N            -> 绝区零壁纸收录\\New Eridan 时尚\\{角色}-{tab}.ext
  时装名标签 (媒介物料/角色展示 里不含通用动作词的标签, 如 从周一到周五)
                       -> 绝区零壁纸收录\\New Eridan 时尚\\{角色}-{标签}.ext
  未归档影像N          -> 绝区零\\未归档影像\\{角色}-未归档影像N.ext
  采访手记N            -> 绝区零\\采访手记\\{角色}-采访手记N.ext
Skipped: 技能/强化/动画/卡片/机制/影画展示(mindscapes_fill 管线)/默认标题/攻略…
系列边界(2026-10 确认): 采访手记官方到雨果篇为止、未归档影像 20 角色已全覆盖,
勿再主动排查缺口。
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hoyo_common import (ROOT_ZZZ, direct_session, dl, ext_of, fetch_page,
                         fetch_tree, mapdesc_items, sanitize)

FASHION_DIR = os.path.join(ROOT_ZZZ, "绝区零壁纸收录", "New Eridan 时尚")
UNARC_DIR = os.path.join(ROOT_ZZZ, "未归档影像")
NOTES_DIR = os.path.join(ROOT_ZZZ, "采访手记")

# generic action/UI labels never collected as 时装名
GENERIC_RE = re.compile(
    r"(待机|入场|退场|登场|特写|战败|动画|强化|档案|卡片|默认|攻略|头像|图标|待机动作|展示\d*$)")
EXACT_SKIP = {"普攻", "闪避", "支援技", "特殊技", "终结技", "核心技", "连携技", "总计",
              "普通攻击强化", "闪避强化", "核心技强化"}


def name_prefix(title):
    """Wiki title -> filename prefix. 日式名不加空格 (星见 雅 -> 星见雅)."""
    p = sanitize(title)
    if re.fullmatch(r"[\u4e00-\u9fff]{2,4} [\u4e00-\u9fff]{1,3}", p):
        p = p.replace(" ", "")
    return p


def classify(grp, tab):
    """tab -> (dest_dir, filename_stem_without_ext) or None to skip."""
    tab = (tab or "").strip()
    if not tab:
        return None
    m = re.fullmatch(r"未归档影像(\d+)", tab)
    if m:
        return "unarc", f"未归档影像{m.group(1)}"
    m = re.fullmatch(r"采访手记(\d+)", tab)
    if m:
        return "notes", f"采访手记{m.group(1)}"
    m = re.fullmatch(r"时装展示(\d+)", tab)
    if m:
        return "fashion", tab
    if grp in ("媒介物料", "角色展示") and tab not in EXACT_SKIP \
            and not GENERIC_RE.search(tab) and not re.fullmatch(r"影画展示\d+", tab):
        return "fashion", tab  # named costume/pose label
    return None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    S = direct_session()
    dirs = {"fashion": FASHION_DIR, "unarc": UNARC_DIR, "notes": NOTES_DIR}
    counts = {"fashion": 0, "unarc": 0, "notes": 0}
    n_new = 0
    for pid, title in fetch_tree(S, 43):
        page = fetch_page(S, pid)
        prefix = name_prefix(title)
        for grp, tab, url in mapdesc_items(page):
            c = classify(grp, tab)
            if not c:
                continue
            kind, stem = c
            fn = f"{prefix}-{sanitize(stem)}.{ext_of(url)}"
            dest = os.path.join(dirs[kind], fn)
            if os.path.exists(dest):
                continue
            counts[kind] += 1
            print(f"[{kind}] {prefix} :: {tab} -> {fn}")
            if mode == "download":
                dl(S, url, dest)
                time.sleep(0.15)
            n_new += 1
    print(f"汇总 fashion={counts['fashion']} unarc={counts['unarc']} "
          f"notes={counts['notes']}，新增 {n_new if mode == 'download' else 0}（dry 未下载）")


if __name__ == "__main__":
    main()
