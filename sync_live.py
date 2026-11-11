# -*- coding: utf-8 -*-
"""从本机活动目录刷新本仓库的策展快照（与初次构建规则一致）。

只拷贝 *.py/*.md/*.json 等代码与真值数据；跳过 __pycache__、运行状态、
调试 PNG、回收站清单。真值目录 results/ 与 trace_masks/ 整目录按扩展名拷。
"""
import glob
import os
import shutil

LIVE = os.path.expanduser(r"~\.zcode\workspace\default")
REPO = os.path.dirname(os.path.abspath(__file__))

# (活动目录相对路径, 仓库内相对路径, 拷贝的扩展名/文件名)
SYNC_MAP = [
    ("zzz-media-pipeline", "zzz-media-pipeline", ["*.py", "README.md"]),
    ("pupilfix", "pupilfix", ["*.py", "*.json", "*.md", "eyeglow_tex_list.txt"]),
    ("rgb-theme-sync", "rgb-theme-sync", ["*.py"]),
]
TRUTH_DIRS = ["results/*.json", "trace_masks/*.png"]  # pupilfix 真值子目录


def is_debug_png(name):
    return name.lower().endswith(".png")  # pupilfix 根目录的 png 全是调试图


def copy_batch(src_glob, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    n = 0
    for p in glob.glob(os.path.join(LIVE, src_glob)):
        name = os.path.basename(p)
        if is_debug_png(name):
            continue
        shutil.copy2(p, os.path.join(dst_dir, name))
        n += 1
    return n


def main():
    total = 0
    for src, dst, pats in SYNC_MAP:
        for pat in pats:
            n = copy_batch(os.path.join(src, pat), os.path.join(REPO, dst))
            print(f"{src}/{pat}: {n}")
            total += n
    for pat in TRUTH_DIRS:
        dst = os.path.join(REPO, "pupilfix", os.path.dirname(pat))
        n = copy_batch(os.path.join("pupilfix", pat), dst)
        print(f"pupilfix/{pat}: {n}")
        total += n
    print(f"total {total} files synced")


if __name__ == "__main__":
    main()
