# -*- coding: utf-8 -*-
"""Shared helpers for ZZZ media pipelines (re-established 2026-10-28).

Network iron rule: miHoYo domestic domains (api-takumi / act-api / fastcdn /
act-upload / bbs-api / minas) go DIRECT — requests must bypass the Clash system
proxy (trust_env=False). Overseas only (sg-public-api / Drive / HoYoLAB) go
through Clash mixed port 127.0.0.1:7897.
"""
import json
import os
import re
import time

import requests

PIPE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(PIPE, "state")
STAGING = os.path.join(PIPE, "staging", "zzz_wp_staging")
ROOT_ZZZ = r"E:\Pictures\壁纸\绝区零"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
WIKI_API = "https://act-api-takumi-static.mihoyo.com"
ZZZ_CN_APP = "https://api-takumi-static.mihoyo.com/content_v2_user/app/706fd13a87294881"
MYS_POST = "https://bbs-api.miyoushe.com/post/wapi/getPostFull"
MYS_USER_POSTS = "https://bbs-api.miyoushe.com/painter/wapi/userPostList"
OFFICIAL_UID = "152039148"  # 绝区零 official miyoushe account


def direct_session(extra_headers=None):
    s = requests.Session()
    s.trust_env = False  # never inherit system/Clash proxy for miHoYo domains
    s.headers.update({"User-Agent": UA, "Referer": "https://baike.mihoyo.com/",
                      "x-rpc-wiki_app": "zzz"})
    if extra_headers:
        s.headers.update(extra_headers)
    return s


def get_recycle():
    """Return recycle(*paths) from the established tool; all deletes must go through it."""
    import sys
    sys.path.insert(0, r"E:\Pictures\壁纸\壁纸更新工具")
    from recycle_delete import recycle
    return recycle


# ---------------- wiki ----------------

def fetch_tree(S, cid):
    """Channel tree -> [(entry_page_id, title)]."""
    j = S.get(f"{WIKI_API}/common/blackboard/zzz_wiki/v1/home/content/list",
              params={"app_sn": "zzz_wiki", "channel_id": cid}, timeout=60).json()
    assert j.get("retcode") == 0, (cid, j.get("retcode"), j.get("message"))
    root = j["data"]["list"][0]
    return [(c["content_id"], c["title"])
            for c in (root.get("list") or root.get("children") or [])]


def fetch_page(S, pid):
    """Entry page dict, or None if the entry has no page yet (retcode 0, empty data)."""
    j = S.get(f"{WIKI_API}/hoyowiki/zzz/wapi/entry_page",
              params={"app_sn": "zzz_wiki", "entry_page_id": pid}, timeout=60).json()
    assert j.get("retcode") == 0, (pid, j.get("retcode"), j.get("message"))
    return (j.get("data") or {}).get("page")


def mapdesc_items(page):
    """Yield (group_name, tab_name, full_image_url) for every map_desc image.

    Group names come from template_layout.tab[].module_group[].name; the
    act-upload direct link is the original size (strip ?x-oss-process)."""
    if not page:
        return
    gname = {}
    for tab in page.get("template_layout", {}).get("tab", []):
        for g in tab.get("module_group", []):
            for m in g.get("module", []):
                gname[str(m["id"])] = g.get("name", "")
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
            if isinstance(data, dict) and data.get("list"):
                for item in data["list"]:
                    url = (item.get("image") or "").strip()
                    if url:
                        yield grp, item.get("tab_name", ""), url.split("?x-oss-process")[0]


# ---------------- naming ----------------

CN_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
          "八": 8, "九": 9, "两": 2}
NUMERAL_EXCEPTIONS = ("绝区零", "六分街", "三明治", "一千零一夜", "三倍赏金", "零号·安比")


def cn_to_int(s):
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


def convert_numerals(name):
    """中文数字→阿拉伯数字 for (X) and 第X弹/期/季/章/周; protected names untouched."""
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


_RAD_MAP = {"⾬": "雨", "⾦": "金", "⻝": "食", "⻢": "马", "⻥": "鱼", "⻦": "鸟",
            "⻛": "风", "⻰": "龙", "⻳": "龟", "⻋": "车", "⻔": "门", "⻘": "青",
            "⻜": "飞", "⻬": "齐", "⻯": "竜", "⻲": "龟"}


def sanitize(name):
    for rad, rep in _RAD_MAP.items():
        name = name.replace(rad, rep)
    s = re.sub(r"[\\/:*?\"<>|]", "", name)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    s = s.replace("「 ", "「").replace(" 」", "」")
    s = re.sub(r" (\d)", r"\1", s)  # no space before ordinals
    return s


def ext_of(url):
    m = re.search(r"\.((?:png|jpe?g|webp|gif))(?![\w.])", url, re.I)
    return (m.group(1).lower() if m else "png").replace("jpeg", "jpg")


# ---------------- state ----------------

def load_state(name, default):
    p = os.path.join(STATE_DIR, name)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_state(name, obj):
    os.makedirs(STATE_DIR, exist_ok=True)
    p = os.path.join(STATE_DIR, name)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


# ---------------- download ----------------

def dl(S, url, dest, attempts=4):
    """Stream download with retries; resumes by skipping existing non-empty files.
    On final failure the .part file is left in place (deletes must use recycle bin)."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return "skip"
    tmp = dest + ".part"
    err = None
    for i in range(attempts):
        try:
            with S.get(url, stream=True, timeout=(20, 300)) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 19):
                        if chunk:
                            f.write(chunk)
            os.replace(tmp, dest)
            return "ok"
        except Exception as e:
            err = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"download failed {url}: {err}")


# ---------------- miyoushe official account ----------------

def iter_posts(S, uid=OFFICIAL_UID, size=20):
    """Yield userPostList items for a miyoushe account (pagination offset/is_last)."""
    offset = "0"
    while True:
        j = S.get(MYS_USER_POSTS, params={"uid": uid, "offset": offset, "size": size,
                                          "gid": "6"}, timeout=60).json()
        assert j.get("retcode") == 0, (uid, j.get("retcode"), j.get("message"))
        d = j.get("data") or {}
        posts = d.get("list") or []
        if not posts:
            return
        for it in posts:
            yield it
        if d.get("is_last"):
            return
        nxt = d.get("offset")
        if not nxt or str(nxt) == str(offset):
            return
        offset = str(nxt)


def post_detail(S, post_id):
    """getPostFull -> data.post dict (gids=8 is ZZZ). Fetch right before using
    any signed vod/media URL — they expire."""
    j = S.get(MYS_POST, params={"gids": "8", "post_id": post_id}, timeout=60).json()
    assert j.get("retcode") == 0, (post_id, j.get("retcode"), j.get("message"))
    return j.get("data", {}).get("post") or {}


# ---------------- minas share-link client (from sync_v3) ----------------

class Minas:
    """minas.mihoyo.com share-link client: csrf -> password -> recursive dirents -> dl=1."""

    def __init__(self):
        self.s = {}

    def _sess(self, token, password):
        if token in self.s:
            return self.s[token]
        s = requests.Session()
        s.trust_env = False
        s.headers.update({"User-Agent": UA})
        r0 = s.get(f"https://minas.mihoyo.com/d/{token}/", timeout=30)
        csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r0.text).group(1)
        s.post(f"https://minas.mihoyo.com/d/{token}/",
               data={"csrfmiddlewaretoken": csrf, "token": token, "password": password},
               headers={"Referer": f"https://minas.mihoyo.com/d/{token}/"}, timeout=30)
        self.s[token] = s
        return s

    def walk(self, token, password, path="/"):
        s = self._sess(token, password)
        r = s.get(f"https://minas.mihoyo.com/api/v2.1/share-links/{token}/dirents/",
                  params={"path": path}, timeout=30)
        if r.status_code != 200:
            return
        for d in r.json().get("dirent_list") or []:
            fp = d.get("file_path") or ""
            if d.get("is_dir"):
                yield from self.walk(token, password, fp)
            else:
                yield fp

    def download(self, token, password, fp):
        s = self._sess(token, password)
        r = s.get(f"https://minas.mihoyo.com/d/{token}/files/", params={"p": fp, "dl": "1"},
                  timeout=300)
        return r.content if r.status_code == 200 and len(r.content) > 1000 else None


# password regex MUST stay narrow: \S+ swallows HTML and loses whole packs
MINAS_LINK_RE = re.compile(r"minas\.mihoyo\.com/d/([0-9A-Za-z]+)")
MINAS_PWD_RE = re.compile(r"密码[：:]\s*([A-Za-z0-9@#._\-]+)")
