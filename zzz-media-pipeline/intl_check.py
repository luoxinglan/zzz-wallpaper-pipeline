# -*- coding: utf-8 -*-
"""intl (sg-public ch288) new-post check (re-homed 2026-10-28).

Overseas endpoint -> goes through Clash proxy 127.0.0.1:7897 (direct fails).
Writes state/intl_ch288_fresh.json for merge_staging.py to promote into the
tmp_gdrive all_posts.json state. Fresh posts themselves are fetched with the
Drive tools in E:\\Pictures\\壁纸\\壁纸更新工具\\tmp_gdrive\\.
"""
import json
import os
import time

import requests

PIPE = os.path.dirname(os.path.abspath(__file__))
STATE = r"E:\Pictures\壁纸\壁纸更新工具\tmp_gdrive\all_posts.json"
OUT = os.path.join(PIPE, "state", "intl_ch288_fresh.json")

old = json.load(open(STATE, encoding="utf-8"))
newest_old = max(p["iInfoId"] for p in old)
print("state newest id:", newest_old)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
BASE = "https://sg-public-api-static.hoyoverse.com/content_v2_user/app/3e9196a4b9274bd7"
proxies = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}


def fetch(channel_id, page):
    # 2026-11-08 fix: 旧参数(channelId/pageNum)已失效返回1001，必须用 iChanId/iPageSize/iPage/sLangKey
    r = requests.get(f"{BASE}/getContentList",
                     params={"iChanId": channel_id, "iPageSize": 50, "iPage": page,
                             "sLangKey": "zh-cn"},
                     headers={"User-Agent": UA}, proxies=proxies, timeout=40)
    return r.json()


j = fetch(288, 1)
print("retcode:", j.get("retcode"), "msg:", j.get("message"))
lst = (j.get("data") or {}).get("list") or []
print("page1 items:", len(lst))
if lst:
    posts = []
    stop = False
    page = 1
    while not stop:
        j = fetch(288, page)
        lst = (j.get("data") or {}).get("list") or []
        if not lst:
            break
        for it in lst:
            pid = it.get("iInfoId")
            title = it.get("sTitle")
            start = (it.get("dtStartTime") or "")[:10]
            posts.append({"iInfoId": pid, "sTitle": title, "dtStartTime": start, "chan": 288})
            if pid and pid <= newest_old:
                stop = True
                break
        page += 1
        time.sleep(0.4)
    fresh = [p for p in posts if p["iInfoId"] > newest_old]
    fresh.sort(key=lambda p: -p["iInfoId"])
    print(f"new since state: {len(fresh)}")
    for p in fresh:
        print(" ", p["iInfoId"], p["dtStartTime"], p["sTitle"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(posts, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
