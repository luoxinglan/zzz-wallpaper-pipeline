# zzz-media-pipeline

绝区零媒体库更新管线（2026-10-28 重建于永久目录；总纲见技能 `zzz-media-update`，手册见 `..\自动化工作流手册.md`）。

## 脚本

| 脚本 | 指令 | 说明 |
|---|---|---|
| wiki_wallpaper_fetch.py | 更新壁纸 | wiki 频道98/99 增量 → staging；之后跑 merge_staging.py |
| merge_staging.py | （壁纸后置） | 暂存并库：新下载为准、md5 重删回收站、「新换旧」先回收再移入；升级 manifest |
| intl_check.py | 更新壁纸（intl） | sg ch288 新帖检查 → state/intl_ch288_fresh.json；走 Clash 7897 |
| mindscapes_fill.py | 更新影画 | wiki 频道43 → 意像影画 tab 补缺 → 意向影画\原图\；之后 upscale_mindscapes.py（E盘工具） |
| wiki_videos.py | 更新视频 | wiki 频道73/72 → 米游社 vod 最高清 → 视频\；entry_map 缓存词条→post_id |
| news_posters_hires.py | 更新海报 | 官网 ch278/279/280 正文大图 → 新闻海报\；3线程断点，全量回填数小时 |
| account_emotes.py | 更新表情包/头像 | 官方账号 uid=152039148 帖图 + minas 全尺寸包 → 表情包\ / 官方头像\ |
| wiki_agent_media.py | 更新代理人媒体 | 时装展示N/时装名→New Eridan 时尚；未归档影像N；采访手记N；其余跳过 |
| mys_unarc_fill.py | （兜底） | 米游社官方帖补 未归档影像 |
| hoyo_common.py | 共享 | 直连 session、wiki API、命名规范化、状态读写、Minas 客户端、回收站 helper |

## 约定

- 用法统一 `python <script> dry|download`（dry 默认）；幂等可重跑。
- miHoYo 国内域名直连（trust_env=False）；intl/Drive 走 Clash 127.0.0.1:7897。
- 一切删除走回收站（hoyo_common.get_recycle → E 盘 recycle_delete.py）。
- 状态文件在 `state\`，中断重跑即续。
- wiki 陷阱：模块组名「意像影画」(像)；库目录「意向影画」(向)。
