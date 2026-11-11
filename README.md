# ZZZ Wallpaper Pipeline

绝区零（Zenless Zone Zero）Wallpaper Engine 动态壁纸生产工具链：从官方媒体采集、
眼形光斑（eyeglow）烘焙，到 RGB 灯效联动的全套脚本。**私有仓库**——内容含游戏衍生的
真值数据与描线蒙版，请勿公开分发。

## 目录结构

| 目录 | 内容 |
|---|---|
| `zzz-media-pipeline/` | 官方 wiki / 米游社 / hoyo 媒体采集管线（壁纸、意向影画、视频、新闻海报、表情包、头像、时装）。`hoyo_common.py` 为共享底座；三段式运行：`dry` 预览 → `download` → `merge`（回收站合并），断点状态存本机 `state/`（不入库） |
| `pupilfix/` | WE 壁纸"眼睛彩色区域音频闪烁"工具链：bg2 虹膜检测、eyeglow 烘焙（apply_v41b）、TRACE 手动描线（bake_trace）、NCC 对齐、批量三处同步（batch_sync）。`results/` = 61 个项目的人工眼坐标真值；`trace_masks/` = 23 张用户描线蒙版真值；`circle_overrides.json` = 逐眼参数覆盖表 |
| `rgb-theme-sync/` | WE 主题色 → 雷蛇 Chroma → MSI/iGame RGB 全链联动 |

## 本仓库与活动目录的关系

仓库是活动目录的**策展快照**（只含代码 + 真值数据，不含调试图片/缓存/运行状态）。
本机活动位置（Windows）：

- `%USERPROFILE%\.zcode\workspace\default\zzz-media-pipeline\`
- `%USERPROFILE%\.zcode\workspace\default\pupilfix\`
- `%USERPROFILE%\.zcode\workspace\default\rgb-theme-sync\`

刷新快照：`python sync_live.py`（按内置 SYNC_MAP 从活动目录重新拷贝，规则与本仓库
初次构建一致：只取 `*.py/*.md/*.json` + 真值目录，跳过 `__pycache__/state/staging/`
调试 PNG 与回收站清单）。

## 环境与复用说明

- Python 3.11+，依赖：`numpy / pillow / scipy / opencv-python / requests`
- 脚本内含**本机硬编码路径**（Wallpaper Engine 项目目录、图库盘符），复用需改各自
  头部的路径常量
- 虹膜分割模型（新角色眼坐标草稿）在配套仓库 [zzz-iris](https://github.com/luoxinglan/zzz-iris)
- `pupilfix/results/*.json` 的 `ax/ay/bx/by/r_pct` 均为 bg2 画布百分比坐标，
  与 zzz-iris 的推理输出同基准

## 安全约定（沿用本机工作流铁律）

- 一切删除走回收站（`send2trash` / recycle 脚本），禁止 `unlink/rmtree/del/rd`
- 渲染器加载会自动把同名 png 编译成 `.tex`，重烘焙 png 后必须回收 `.tex`
- 改烘焙坐标必须三处同步：config.json Monitor0 + project.json 默认值 + frag 常量
