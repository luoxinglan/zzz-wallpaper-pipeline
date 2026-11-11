# -*- coding: utf-8 -*-
"""ZZZ wiki wallpaper incremental fetch (built 2026-10-13, re-homed 2026-10-28).

Channels: 98 = 壁纸收录, 99 = 好感壁纸.
Usage:
  python wiki_wallpaper_fetch.py dry       # fetch wiki, diff vs old manifest, report only
  python wiki_wallpaper_fetch.py download  # diff + download new files into staging folder
State:
  old manifest: state\\wiki_manifest.json (last fully merged state)
  new manifest: state\\wiki_manifest_new.json (written by this script)
  staging:     staging\\zzz_wp_staging\\<绝区零壁纸收录 mirror structure>
  merge with:  merge_staging.py (moves staging into E:\\Pictures library, promotes manifest)
miHoYo domains go DIRECT (no Clash proxy). Re-run skips already-staged files.
"""
import json
import os
import re
import sys
import hashlib
import time
import concurrent.futures as cf
import requests

PIPE = os.path.dirname(os.path.abspath(__file__))
OLD_MANIFEST = os.path.join(PIPE, "state", "wiki_manifest.json")
NEW_MANIFEST = os.path.join(PIPE, "state", "wiki_manifest_new.json")
STAGING = os.path.join(PIPE, "staging", "zzz_wp_staging")
LOG = os.path.join(PIPE, "state", "wiki_incremental.log")

API = "https://act-api-takumi-static.mihoyo.com"
S = requests.Session()
S.trust_env = False  # miHoYo must bypass Clash system proxy
S.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://baike.mihoyo.com/",
                  "x-rpc-wiki_app": "zzz"})

CHANNELS = {98: "壁纸收录", 99: "好感壁纸"}

CN_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
          "八": 8, "九": 9, "两": 2}

def cn_to_int(s):
    """Convert simple CJK numeral strings (up to 99) to int; None if not pure."""
    if not s:
        return None
    if all(ch in "〇零一二三四五六七八九十" for ch in s):
        if "十" in s:
            left, _, right = s.partition("十")
            tens = CN_NUM.get(left, 1) if left else 1
            ones = CN_NUM.get(right, 0) if right else 0
            return tens * 10 + ones
        if len(s) == 1:
            return CN_NUM.get(s)
    return None

NUMERAL_EXCEPTIONS = ("绝区零", "六分街", "三明治", "一千零一夜", "三倍赏金", "零号·安比")

def convert_numerals(name):
    """中文数字→阿拉伯数字 for (X) and 第X弹/期/季/章/周 patterns; protected names untouched."""
    for ex in NUMERAL_EXCEPTIONS:
        if ex in name:
            return name

    def paren_sub(m):
        n = cn_to_int(m.group(1))
        return f"({n})" if n is not None else m.group(0)

    def ord_sub(m):
        n = cn_to_int(m.group(1))
        return f"第{n}{m.group(2)}" if n is not None else m.group(0)

    name = re.sub(r"[（(]([〇零一二三四五六七八九十]+)[)）]", paren_sub, name)
    name = re.sub(r"第([〇零一二三四五六七八九十]+)(弹|期|季|章|周)", ord_sub, name)
    return name

# Kangxi radicals / CJK compat radicals -> CJK unified (only forms seen in wiki titles)
_RAD_MAP = {"⾬": "雨", "⾦": "金", "⻝": "食", "⻢": "马", "⻥": "鱼", "⻦": "鸟",
            "⻛": "风", "⻰": "龙", "⻳": "龟", "⻋": "车", "⻔": "门", "⻘": "青",
            "⻜": "飞", "⻬": "齐", "⻯": "竜", "⻲": "龟"}

def sanitize(name):
    for rad, rep in _RAD_MAP.items():
        name = name.replace(rad, rep)
    s = name
    s = re.sub(r"[\\/:*?\"<>|]", "", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    s = s.replace("「 ", "「").replace(" 」", "」")
    s = re.sub(r" (\d)", r"\1", s)  # no space before ordinals
    return s


def month_special(group, tab):
    """月历 group/tab -> canonical filename stem, else None."""
    m = re.fullmatch(r"(\d{4})PC版?壁纸收录", group)
    if m:
        mm = re.fullmatch(r"(\d{1,2})月", tab)
        if mm:
            return f"月历-{m.group(1)}年{int(mm.group(1))}月-PC版"
    m = re.fullmatch(r"(\d{4})手机版壁纸收录", group)
    if m:
        mm = re.fullmatch(r"(\d{1,2})月", tab)
        if mm:
            return f"月历-{m.group(1)}年{int(mm.group(1))}月-手机版"
    return None


def fetch_channel(cid):
    r = S.get(f"{API}/common/blackboard/zzz_wiki/v1/home/content/list",
              params={"app_sn": "zzz_wiki", "channel_id": cid}, timeout=60)
    j = r.json()
    assert j.get("retcode") == 0, (cid, j.get("retcode"), j.get("message"))
    root = j["data"]["list"][0]
    return [(c["content_id"], c["title"]) for c in (root.get("list") or root.get("children") or [])]


def fetch_entry(page_id):
    r = S.get(f"{API}/hoyowiki/zzz/wapi/entry_page",
              params={"app_sn": "zzz_wiki", "entry_page_id": page_id}, timeout=60)
    j = r.json()
    assert j.get("retcode") == 0, (page_id, j.get("retcode"), j.get("message"))
    return j["data"]["page"]


def parse_entry(page, channel):
    """Return images [[group, tab, url]], videos [[name, url]] (extras mirror videos)."""
    gname = {}
    for tab in page.get("template_layout", {}).get("tab", []):
        for g in tab.get("module_group", []):
            nm = g.get("name", "")
            for m in g.get("module", []):
                gname[str(m["id"])] = nm
    images, videos = [], []
    for mod in page.get("modules", []):
        grp = gname.get(str(mod.get("id", "")), "")
        for comp in mod.get("components", []):
            raw = comp.get("data")
            if not isinstance(raw, str):
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            if comp.get("component_id") == "map_desc" or "list" in data:
                for item in data.get("list") or []:
                    url = (item.get("image") or "").strip()
                    if not url:
                        continue
                    url = url.split("?x-oss-process")[0]
                    tab = item.get("tab_name", "")
                    stem = month_special(grp, tab) if grp else None
                    if stem:
                        images.append([stem, "", url])
                    else:
                        images.append([grp, tab, url])
            rt = data.get("rich_text") or ""
            for vm in re.finditer(r'data-video-url="([^"]+)"', rt):
                url = vm.group(1).split("?x-oss-process")[0]
                name = "壁纸展示" if channel == "好感壁纸" else grp
                if name:
                    videos.append([name, url])
    return images, videos


def ext_of(url):
    m = re.search(r"\.((?:png|jpe?g|webp|gif|mp4))(?![\w.])", url, re.I)
    return (m.group(1).lower() if m else "png").replace("jpeg", "jpg")


def safe_stem(a, b):
    stem = f"{a}-{b}" if b else a
    return sanitize(convert_numerals(stem))


def build_manifest():
    entries = []
    for cid, channel in CHANNELS.items():
        items = fetch_channel(cid)
        print(f"channel {cid} {channel}: {len(items)} entries", flush=True)
        for pid, title in items:
            page = fetch_entry(pid)
            images, videos = parse_entry(page, channel)
            entries.append({"channel": channel, "id": pid, "title": title,
                            "wiki_name": title, "folder": title,
                            "images": images, "videos": videos,
                            "extras": [[n, u] for n, u in videos]})
            print(f"  {title}: {len(images)}图 {len(videos)}视频", flush=True)
            time.sleep(0.15)
    return entries


def old_url_set(oe):
    s = set()
    for a, b, u in oe.get("images", []):
        s.add(u)
    for n, u in oe.get("videos", []):
        s.add(u)
    for n, u in oe.get("extras", []):
        s.add(u)
    return s


def diff(new_entries, old_entries):
    old_by_id = {e["id"]: e for e in old_entries}
    plan = []  # (entry, kind, name_pair, url)
    for e in new_entries:
        oe = old_by_id.get(e["id"])
        known = old_url_set(oe) if oe else set()
        for a, b, u in e["images"]:
            if u not in known:
                plan.append((e, "img", (a, b), u))
        for n, u in e["videos"]:
            if u not in known:
                plan.append((e, "vid", (n, ""), u))
    return plan


def relpath_for(entry, kind, names, url):
    folder = sanitize(convert_numerals(entry["folder"]))
    if entry["channel"] == "好感壁纸":
        sub = os.path.join("绝区零壁纸收录", "好感壁纸", folder)
        if kind == "vid":
            return os.path.join(sub, "壁纸展示.mp4")
        a, b = names
        return os.path.join(sub, safe_stem(a, b) + "." + ext_of(url))
    sub = os.path.join("绝区零壁纸收录", folder)
    a, b = names
    if kind == "vid":
        return os.path.join(sub, safe_stem(a, b) + ".mp4")
    return os.path.join(sub, safe_stem(a, b) + "." + ext_of(url))


def md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


def download_one(item):
    entry, kind, names, url, rel = item
    dest = os.path.join(STAGING, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return ("skip", rel)
    tmp = dest + ".part"
    for attempt in range(4):
        try:
            with S.get(url, stream=True, timeout=(20, 300)) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 19):
                        if chunk:
                            f.write(chunk)
            os.replace(tmp, dest)
            return ("ok", rel)
        except Exception as e:
            if attempt == 3:
                return ("fail", f"{rel} :: {e}")
            time.sleep(3 * (attempt + 1))
    return ("fail", rel)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    logf = open(LOG, "a", encoding="utf-8")

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + "\n")

    old = json.load(open(OLD_MANIFEST, encoding="utf-8"))
    log(f"== run {time.strftime('%Y-%m-%d %H:%M:%S')} mode={mode} old_entries={len(old)}")
    new = build_manifest()
    json.dump(new, open(NEW_MANIFEST, "w", encoding="utf-8"), ensure_ascii=False)
    tot_img = sum(len(e["images"]) for e in new)
    tot_vid = sum(len(e["videos"]) for e in new)
    log(f"共 {len(new)} 词条, {tot_img} 图, {tot_vid} 视频")

    old_by_id = {e["id"]: e for e in old}
    for e in new:
        if e["id"] not in old_by_id:
            log(f"新词条 [{e['channel']}] {e['title']} (id={e['id']})")

    plan = diff(new, old)
    log(f"新增待下载 {len(plan)} 个文件:")
    for entry, kind, names, url in plan:
        a, b = names
        label = f"{a}-{b}" if b else a
        log(f"  [{entry['channel']}] {entry['folder']} :: {label} :: {kind} :: {url}")

    if mode != "download":
        log("dry 模式结束，未下载。")
        return
    if not plan:
        log("无新增，结束。")
        return

    items = [(e, k, n, u, relpath_for(e, k, n, u)) for e, k, n, u in plan]
    ok = skip = fail = 0
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        for status, rel in ex.map(download_one, items):
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
                log(f"  下载失败: {rel}")
            if (ok + skip + fail) % 25 == 0:
                log(f"  进度 完成{ok} 跳过{skip} 失败{fail} / {len(items)}")
    log(f"完成: 成功{ok} 跳过{skip} 失败{fail}")
    logf.close()
    if fail:
        sys.exit(2)


if __name__ == "__main__":
    main()
