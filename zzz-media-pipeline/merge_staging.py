# -*- coding: utf-8 -*-
"""Merge staged ZZZ wallpaper downloads into E:\\Pictures\\壁纸\\绝区零 (re-homed 2026-10-28).

Rules (established workflow, 2026-10-13):
  - new download wins on name collision with different content (old file -> recycle bin)
  - md5-identical files -> staged copy discarded (recycle bin)
  - old library files not present in this batch are kept
  - intl Roxie post showcase images: perceptual-hash dedupe vs the Drive 4K pack
All deletions go through the recycle bin. After merge, state\\wiki_manifest_new.json
is promoted to wiki_manifest.json.
"""
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, r"E:\Pictures\壁纸\壁纸更新工具")
from recycle_delete import recycle  # noqa: E402

from PIL import Image

PIPE = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.join(PIPE, "staging", "zzz_wp_staging")
SRC_ROOT = os.path.join(STAGING, "绝区零壁纸收录")
TARGET_ROOT = r"E:\Pictures\壁纸\绝区零\绝区零壁纸收录"
POST_DIR = os.path.join(STAGING, "_intl_post")


def md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


def ahash(path, size=8):
    im = Image.open(path).convert("L").resize((size, size), Image.LANCZOS)
    px = list(im.getdata())
    avg = sum(px) / len(px)
    return [1 if p > avg else 0 for p in px]


def hamming(a, b):
    return sum(x != y for x, y in zip(a, b))


def main():
    moved = dup_recycled = replaced = 0
    recycle_queue = []
    plan = []

    if not os.path.isdir(SRC_ROOT):
        print("staging 为空，无事可做")
    else:
        for dirpath, _dirs, files in os.walk(SRC_ROOT):
            for fn in files:
                if fn.endswith(".part") or fn.startswith("~"):
                    continue
                src = os.path.join(dirpath, fn)
                parts = os.path.relpath(src, SRC_ROOT).split(os.sep)
                # flatten Roxie resolution subfolders: 主题壁纸\主题壁纸-洛克茜-<res>\<file>
                if (len(parts) == 3 and parts[0] == "主题壁纸"
                        and parts[1].startswith("主题壁纸-洛克茜-")):
                    parts = [parts[0], parts[2]]
                plan.append((src, os.path.join(TARGET_ROOT, *parts)))

    for src, tgt in plan:
        os.makedirs(os.path.dirname(tgt), exist_ok=True)
        if not os.path.exists(tgt):
            shutil.move(src, tgt)
            moved += 1
            print("+", os.path.relpath(tgt, TARGET_ROOT))
        elif md5(src) == md5(tgt):
            recycle_queue.append(src)
            dup_recycled += 1
            print("=", os.path.relpath(tgt, TARGET_ROOT), "(md5 相同，弃暂存)")
        else:
            # 「新换旧」铁律（2026-10-28 事故）：旧文件必须先回收、再移入新文件。
            # 先覆盖后回收会把新文件送进回收站且旧文件已被覆盖，双份全丢。
            recycle(tgt)
            shutil.move(src, tgt)
            replaced += 1
            print("*", os.path.relpath(tgt, TARGET_ROOT), "(新下载为准，旧文件回收站)")

    # intl post showcase images vs merged Drive 4K pack (_intl_post\<tag>\*.jpg)
    post_merged = post_dup = 0
    if os.path.isdir(STAGING):
        for tag in os.listdir(STAGING):
            pdir = os.path.join(STAGING, tag)
            if not (tag.startswith("_intl_post") and os.path.isdir(pdir)):
                continue
            ref_hashes = []
            ref_dir = os.path.join(TARGET_ROOT, "主题壁纸")
            if os.path.isdir(ref_dir):
                for fn in os.listdir(ref_dir):
                    if fn.startswith("主题壁纸-洛克茜-3840x2160-") and fn.lower().endswith((".jpg", ".png")):
                        ref_hashes.append(ahash(os.path.join(ref_dir, fn)))
            for fn in sorted(os.listdir(pdir)):
                src = os.path.join(pdir, fn)
                if not os.path.isfile(src):
                    continue
                h = ahash(src)
                if any(hamming(h, r) <= 6 for r in ref_hashes):
                    recycle_queue.append(src)
                    post_dup += 1
                    print("=", "帖子图", fn, "(与 Drive 4K 包重复，弃暂存)")
                else:
                    tgt = os.path.join(ref_dir, f"主题壁纸-洛克茜-3840x2160-帖子-{fn.replace('.jpg', '')}.jpg")
                    shutil.move(src, tgt)
                    post_merged += 1
                    print("+", f"主题壁纸\\{os.path.basename(tgt)} (帖子独有)")

    if recycle_queue:
        for i in range(0, len(recycle_queue), 40):
            recycle(*recycle_queue[i:i + 40])

    # prune now-empty staging dirs
    if os.path.isdir(STAGING):
        for dirpath, dirs, files in os.walk(STAGING, topdown=False):
            if not os.listdir(dirpath):
                os.rmdir(dirpath)

    print(json.dumps({
        "moved": moved, "md5_dup_recycled": dup_recycled,
        "replaced_old": replaced,
        "post_merged": post_merged, "post_dup_recycled": post_dup,
    }, ensure_ascii=False))

    # ---- state promotion ----
    newm = os.path.join(PIPE, "state", "wiki_manifest_new.json")
    oldm = os.path.join(PIPE, "state", "wiki_manifest.json")
    if os.path.exists(newm):
        os.replace(newm, oldm)
        print("wiki_manifest.json 已更新")

    state_p = r"E:\Pictures\壁纸\壁纸更新工具\tmp_gdrive\all_posts.json"
    fresh_p = os.path.join(PIPE, "state", "intl_ch288_fresh.json")
    if os.path.exists(fresh_p):
        old = json.load(open(state_p, encoding="utf-8"))
        have = {p["iInfoId"] for p in old}
        fresh = json.load(open(fresh_p, encoding="utf-8"))
        add = [p for p in fresh if p["iInfoId"] not in have]
        old.extend(add)
        json.dump(old, open(state_p, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"intl 状态已更新 (+{len(add)} 帖)")


if __name__ == "__main__":
    main()
