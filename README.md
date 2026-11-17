# ZZZ Wallpaper Pipeline

绝区零（Zenless Zone Zero）Wallpaper Engine 动态壁纸**生产工具链**：为 60+ 个
「意象影画」动态壁纸项目提供官方媒体采集、眼形光斑（eyeglow）烘焙、RGB 灯效联动
三条生产线。虹膜分割模型在配套仓库
[zzz-iris](https://github.com/luoxinglan/zzz-iris)。

> **私有仓库**：内容含游戏衍生的真值数据（眼坐标、描线蒙版）与游戏图训练的模型
> 权重引用，请勿公开分发。

---

## 背景：这套工具链服务什么

本机 Wallpaper Engine 里有 60+ 个自制项目 `zzz_mindscape_NN_官方全名`（编号 01~68
含空缺），源自工坊模板 3395151088，全部为统一的 v29/v31 体系：

- 每个项目 `materials/` 内置三张同构底图：`bg1`（0 影剪影层）/ `bg2`（3 影黑白+
  彩色虹膜）/ `bg3`（6 影全彩），经 v33 内容配准**像素级对齐**（这也是配套模型仓库
  免费标注的前提）。
- 功能件：angleband 蒙版分区、音频柱、时钟三件套、瞳孔音频脉动（眼闪）。
- 每日生产环节：官方媒体同步入库 → 新角色壁纸做眼闪 → 全屋 RGB 灯随壁纸变色。

三条生产线各对应本仓库一个模块目录，另有一个把三者从活动目录策展进仓库的
快照脚本。

| 目录 | 内容 |
|---|---|
| `zzz-media-pipeline/` | 官方 wiki / 米游社 / hoyo 媒体采集管线（壁纸、意向影画、视频、新闻海报、表情包、头像、时装、未归档影像、采访手记、intl 独有） |
| `pupilfix/` | 「眼睛彩色区域音频闪烁」工具链：眼坐标真值、eyeglow 烘焙、TRACE 手动描线、批量同步 |
| `rgb-theme-sync/` | WE 主题色 → 雷蛇 Chroma → MSI/iGame RGB 全链联动 |
| `sync_live.py` | 从本机活动目录重刷本仓库快照 |

## 设计思想

1. **仓库 = 活动目录的策展快照**。代码和真值入库；调试图片、缓存、运行状态
   （`state/`、`staging/`、`__pycache__`）一律不入库。活动目录在本机
   `%USERPROFILE%\.zcode\workspace\default\` 下的 `zzz-media-pipeline/`、
   `pupilfix/`、`rgb-theme-sync/`，日常开发都在那边，仓库靠 `sync_live.py` 定期
   重刷。**快照反映 2026-11-11 状态**；v42+ 的新脚本（存量修复、bg3 基准重烘焙）
   尚在活动目录，待下次刷新入库。
2. **真值是一等公民**。几个月人工积累的三份资产全部入库：
   - `pupilfix/results/*.json`：61 个项目的眼坐标真值（ax/ay/bx/by/r_pct，
     bg2 画布百分比坐标）；
   - `pupilfix/trace_masks/NN_mask.png`：23 张用户桌面描线虹膜蒙版真值；
   - `pupilfix/circle_overrides.json`：逐眼参数覆盖表。
   配套模型仓库的训练数据直接以它们为种子。
3. **删除一律走回收站**，禁止 `unlink/rmtree/del/rd`；「新换旧」必须先回收旧文件
   再移入新文件（先覆盖再按目标路径回收会把新文件送进回收站且旧文件已被覆盖，
   双份全丢——2026-10-28 12 张壁纸靠回收站 COM 救回的事故教训）。
4. **采集三段式**：`dry` 预览 → `download` → `merge`，断点状态存本机 `state/`
   （不入库），幂等可重跑、中断续跑。
5. **渲染端铁律**（违反即事故，全部实锤断案过）：
   - 烘焙坐标**三处同步**：config.json Monitor0 覆盖值 + project.json 默认值 +
     frag 常量 `g_A0/g_B0`，漏一处光斑就被平移到旧坐标（08 号事故）；
   - 附加纹理只能绑**材质级** json，实例级绑定会顶掉输入帧缓冲 → 全屏洗白；
   - 非 POT 散装 png 会被引擎垫大画布导致内容缩移 ~10%，必须重烘焙成 POT +
     frag 乘回 `(W0/POT_W, H0/POT_H)`；
   - `pupils` 效果必须在 depth 之前（结构性重合）；
   - 渲染器加载会自动把同名 png 编译成 `.tex`，**重烘焙 png 后必须回收 `.tex`**，
     否则旧烤片遮蔽新内容。
6. **网络路由约定**：miHoYo 系国内域名（api-takumi/act-api/fastcdn/bbs-api/minas）
   必须直连（urllib 默认吃系统代理会慢 ~40%）；Drive/HoYoLAB 等境外站走 Clash
   `127.0.0.1:7897`。
7. **定时自动化**：媒体库每周四 02:20 定时「全部更新」七管线；模型训练等 GPU
   任务一律排凌晨（晚上用户打游戏）。

---

## 模块一：zzz-media-pipeline（官方媒体采集）

### 用法（指令化）

统一 `python <script> dry|download`（dry 默认先行），幂等可重跑；下载先入
`staging/`，并库走 `merge_staging.py`。

```bash
python wiki_wallpaper_fetch.py dry|download   # wiki 壁纸收录/好感壁纸增量（manifest diff）
python merge_staging.py                       # staging 并库：新下载为准 + md5 重删回收站
python intl_check.py                          # 国际服独有壁纸检查（Clash 代理）
python mindscapes_fill.py                     # 意向影画补缺（之后跑 upscale_mindscapes.py AI 增强）
python wiki_videos.py                         # 角色/游戏视频（wiki → 米游社 vod 最高清）
python news_posters_hires.py                  # 新闻海报正文大图（≥1200px 替换 banner，断点续跑）
python account_emotes.py                      # 官方账号帖图 + minas 全尺寸包（表情包/头像）
python wiki_agent_media.py                    # 时装/未归档影像/采访手记（map_desc 标签分类）
python mys_unarc_fill.py                      # 未归档影像米游社兜底
```

`hoyo_common.py` 为共享底座：直连 session、wiki API 封装、中文数字命名规范化、
断点状态读写、Minas 客户端、回收站 helper。

### 合并规则

- 新下载为准；旧库存量中新下载没有的**保留**；md5 重复的旧文件删除（回收站）。
- 去重要试**空白字符变体**（wiki tab 名与库内旧文件可能只差 ` & `↔`&`、`「 `↔`「`），
  重内容保留库内旧命名。
- intl 帖子展示图与 Drive 包的重复判定须用 aHash（fastcdn 帖图是重压缩版，md5 必不同）。
- 命名全局适用：中文数字统一替换阿拉伯数字（专名不动）。

---

## 模块二：pupilfix（眼形光斑 / 眼闪）

### 效果定义

光斑形状/位置/颜色 = **bg2 眼睛彩色部分**的形状，随视差与眼睛永远重合，亮度随
音乐脉动。烘焙产物 `eyeglow.png`（bg2 像素 ×1.35 预乘 + 羽化 alpha，POT 垫底），
frag 常量 `g_A0/g_B0` 记录双眼坐标，滑块键 `pupulse*` 支持面板微调。

### 新角色三步（自动管线，apply_v41b.py）

1. 定眼坐标存 `results/NN.json`（闭眼角色整体关闭，eyeglow 为空是正确的）；
2. `python apply_v41b.py --proj NN`——自动：烘焙（bg2 sat>0.28&val>0.13 ∩ 眼位
   1.6r，closing、σ 羽化、RGB=bg2×1.35，空则 3.2r 重试）→ POT 垫画布 → 写 frag →
   材质级纹理绑定 → pupils 移到 depth 前。**幂等**：png 在则不重烘焙；
3. 重启渲染器 → 查日志 → 用户放歌目验。

新角色的坐标草稿现在由配套模型仓库生成（`iris_to_eyeglow.py` 出 draft + qc 图，
人工目检后拷入），人工只剩目检与精修。

### TRACE 描线（人工精修手段，bake_trace.py）

用户在**桌面截图**上用纯色笔描出目标虹膜轮廓，系统按描线原样烘焙——彻底终结
"圆盘 vs 虹膜形状"的拟合问题，用户描什么就是什么：

```bash
python bake_trace.py --proj NN --shot 截图.png --color cyan|lime|red|blue|azure|gold \
    [--eyes "sx,sy;sx,sy"(屏幕%)] [--prior "x,y"(图%)] [--minpix 120] \
    [--searchr "8,9"] [--sync(自动杀WE+三处同步+重启)]
```

流程：颜色检测（**必须显式指定笔色**，auto 会被画作同色元素误导）→ 组件按眼位
±7% 过滤 → closing 封口 + fill + dilate → 描线中值替换后 NCC 对齐（视差自动吸收）
→ 映射原生画布 → σ 轮廓平滑 + 羽化 → 暗像素保底烘焙（暗虹膜也发光）。
蒙版留存 `trace_masks/NN_mask.png`，重烘焙时优先复用。

### 管线演进史（为什么长成现在这样）

| 阶段 | 内容 | 教训/产出 |
|---|---|---|
| v36~v40 | 色簇找眼、门限圆盘、手工逐眼调参 | 每轮用户反馈都是"调过头/不到位"的钟摆——定位与大小分两轮收敛 |
| v41（10-18） | 门限+圆拟合+DARK+uniform 多模式 | 暗虹膜不发光根因=烤片沿用 bg2 暗像素；uniform=亮部分位色铺满全膜 |
| **v41b（10-17 定版）** | 烘焙幂等化，成为标准管线 | 用户拍板"以后新角色都按这个方法来" |
| v41k~n（10-18~19） | **TRACE 描线模式上线**，12 批 25 项目全过 | NCC 定位法（截图红圈+FFT 匹配）取代一切目测；异色瞳/旧锚配对/单双眼勘误等 20+ 条铁律沉淀 |
| v42（11-12） | 存量库按用户 wiki 标注重烘焙（45/30/37） | 边缘改向内羽化 σ3.2，多边形不再"棱角分明不像发光" |
| **v43（11-13~14）** | **6 影画（bg3）唯一基准铁律**；全库 55/55 标注投影重烘焙零失败 | 根因：bg2 黑白渲染眼色≠bg3（"蓝眼闪红光"事故）；用户 181 张标注=全库权威真源 |
| v44（11-14） | 07 佩洛伊斯专项（bg3 实为哲版误用 → 改 bg2+女款铃） | 模板 NCC 失败时用内部蓝连通域虹膜定位兜底 |
| 之后 | 新项目坐标草稿 = zzz-iris 模型自动生成 | 人工只剩目检；召回瓶颈见配套仓库 |

### 批量工具

- `batch_sync_v41n.py`：一次杀启同步多项目三处坐标（NNS 改列表即复用）；
- `rebake_v41c.py`：按 trace_masks/overrides 重烘焙；
- `measure_iris.py` / `nudge_masks.py`：眼周局部饱和色块实测虹膜真值 + 微移；
- `zoom_qc.py`：眼部特写 QC。

---

## 模块三：rgb-theme-sync（RGB 灯效）

### 灯效链路（2026-10-29 调通验收）

```
WE LED 插件（Chroma SDK 集成=开）→ Razer Synapse → ①雷蛇鼠标/底座直连
                                                → ②Chroma Connect → MSI Mystic Light（主板+内存）
                                                → ③Chroma Connect → iGame Center（显卡）
```

### LED 恒色层（v42，全量 60/60）

每项目 objects 里插一个**不可见** 32×32 纯白 LED 采样层（visible:false +
copybackground:false——true 会把背景灰混进采样=绯红变浅粉的事故根因），颜色绑独立
属性 **ledcolor**（面板「LED灯光颜色」）——灯与主题色解耦，切壁纸灯=该角色专属色。
属性 order 必须 = 图层设置组头 order + 0.5，写死会掉进意象影画组（56/59 两试点
组头 order 与其余不同，已修复并固化惯例）。

### `chroma_theme_sync.py`（REST 推色器，已退役）

2026-11-07 实测验证：结束推色器进程后灯照样跟色 → WE 原生 Chroma 集成是唯一主控，
REST 推色路径退役，脚本保留作存档与备用（端口 55329 单例锁；恢复=pythonw 直接跑）。

---

## 本仓库与活动目录的关系

仓库是活动目录的**策展快照**（只含代码 + 真值数据）。刷新快照：

```bash
python sync_live.py    # 按内置 SYNC_MAP 从活动目录重新拷贝：
                       # 只取 *.py/*.md/*.json + 真值目录，
                       # 跳过 __pycache__/state/staging/调试 PNG 与回收站清单
```

活动位置：`%USERPROFILE%\.zcode\workspace\default\{zzz-media-pipeline,pupilfix,rgb-theme-sync}`。

## 环境与复用说明

- Python 3.11+，依赖：`numpy / pillow / scipy / opencv-python / requests`（采集管线另需
  `send2trash`）。
- 脚本内含**本机硬编码路径**（Wallpaper Engine 项目目录、图库盘符、conda 环境路径），
  复用需改各自头部的路径常量。
- `pupilfix/results/*.json` 的 `ax/ay/bx/by/r_pct` 均为 bg2 画布百分比坐标，与
  zzz-iris 推理输出同基准。

## 安全约定（沿用本机工作流铁律）

- 一切删除走回收站（`send2trash` / recycle 脚本），禁止 `unlink/rmtree/del/rd`；
- 「新换旧」先回收旧文件再移入新文件；
- 渲染器加载会自动把同名 png 编译成 `.tex`，重烘焙 png 后必须回收 `.tex`；
- 改烘焙坐标必须三处同步：config.json Monitor0 + project.json 默认值 + frag 常量；
- 杀渲染器前先查 config 是否挂播放列表（冷启动播放列表 + 中文路径会黑屏，需
  备份/恢复 playlist）。

## 版本时间线

| 日期 | 里程碑 |
|---|---|
| 2026-10-08~09 | 60 项目 v29 体系定稿（底图直入 materials）；v32 视差统一；v33 bg2/bg3 内容配准 |
| 2026-10-13 | 媒体更新总纲定稿（指令化九管线） |
| 2026-10-17 | 眼闪管线 v41b 定版（幂等烘焙，新角色三步固化） |
| 2026-10-18~19 | TRACE 描线模式上线，12 批 25 项目；zzz-iris v0 同期起步 |
| 2026-10-28 | pupilfix/媒体管线迁入永久目录；本仓库与 zzz-iris 上传 GitHub |
| 2026-10-29 | RGB 全链（WE→Chroma→MSI/iGame）调通验收；v42 LED 恒色层 60/60 |
| 2026-11-07 | REST 推色器退役（WE 原生集成为唯一主控） |
| 2026-11-12~14 | v42 存量修复 → v43 bg3 唯一基准 + 全库 55/55 重烘焙 → v44 07 专项 |
| 2026-11-12~17 | zzz-iris v1→v7 迭代（夜间定时训练，v7 现役） |
| 2026-11-12 起 | 每周四 02:20 定时「全部更新」七管线自动化 |
