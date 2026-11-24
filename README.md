# Forge Pulse · 开源星榜

GitHub / GitLab / Gitee 三平台**每日涨星聚合榜**。原理很简单：每天拍一次快照，今天的星数减去 N 天前的星数就是增量。不依赖任何第三方增量数据，历史可追溯、可回放。

基于 [star-pulse](https://github.com/logic77lhl/star-pulse) 的"快照相减"机制改造，重写了采集层和看板层以支持多平台，仅用 Python 标准库，无需 `pip install`。

---

## 一、快速开始

| 场景 | 操作 |
|---|---|
| **Windows 本地跑一次** | 双击 `一键运行.bat` |
| **看榜单** | 双击 `查看看板.bat`（或直接用浏览器打开 `docs/index.html`） |
| **命令行跑** | `python src/main.py --all` |
| **只重算看板（不联网）** | `python src/main.py --analyze` |
| **自动每天更新** | 推到 GitHub 仓库，启用 `.github/workflows/daily.yml`，每天北京时间 04:00 自动采集并提交 |

要求：Python 3.9+（本机 3.11 已验证）。**首次运行就能出榜**——项目内置了 31 天真实 GitHub 历史快照作为冷启动数据。

---

## 二、目录结构

```
forge-pulse/
├── 一键运行.bat          ← Windows 双击这个
├── 查看看板.bat          ← 双击看榜单
├── config/
│   ├── settings.json     ← 平台开关、请求数量、时区
│   └── watchlist.txt     ← 固定追踪的仓库清单
├── data/
│   ├── snapshots/        ← 每日快照（事实来源，别删）
│   │   └── 2026-11-23.json
│   ├── leaderboard.json  ← 算好的榜单（程序写，不用手改）
│   └── leaderboard.js    ← 看板读的数据（file:// 下用）
├── docs/index.html       ← 看板（双击打开）
├── src/
│   ├── main.py           ← 一键入口
│   ├── collectors.py     ← 三平台采集器
│   ├── analyze.py        ← 增量计算
│   ├── http_client.py    ← 限流感知请求
│   └── render.py         ← 看板生成
└── .github/workflows/daily.yml  ← 定时更新
```

---

## 三、怎么改配置

### 1. 加追踪仓库：`config/watchlist.txt`

每行一个，格式 `平台:owner/repo`，不写平台默认 GitHub：

```
facebook/react                    # 等于 github:facebook/react
gitlab:gitlab-org/gitlab
gitee:jeelowcode/JeeLowCode
```

### 2. 调平台开关与数量：`config/settings.json`

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `github.token` | 空 | **建议填**。匿名只有 60 次/小时，填 PAT 后 5000 次/小时 |
| `github.trending_enabled` | true | 抓 GitHub Trending 页找当期热点，不消耗 REST 配额 |
| `github.trending_limit` | 30 | Trending 仓库数量，每个还要发 1 次 API 补星数 |
| `github.search_enabled` | false | 是否用 Search API 找新项目，默认关以省配额 |
| `gitlab.top_n` | 40 | GitLab 按星数排序的探索榜取前 N 个，**1 次请求**搞定 |
| `gitee.enabled` | true | Gitee 逐个读种子仓库详情，匿名 60 次/小时 |
| `board.tz_offset_hours` | 8 | 日期归属时区，8 = 北京时间 |

---

## 四、数据口径与已知限制

| 平台 | 候选发现 | 星数接口 | 限制 |
|---|---|---|---|
| GitHub | Trending 页 + 追踪清单 + 可选 Search API | `/repos/{owner}/{repo}` | 匿名 60 次/小时；**建议配 token** |
| GitLab | 探索 API 按 `star_count` 排序 | 同一个探索接口返回 | 无需 token，最省配额 |
| Gitee | **没有公开探索 API**，用追踪清单 | `/api/v5/repos/{owner}/{repo}` | 匿名 60 次/小时；想加项目就写进 `watchlist.txt` |

- **首次运行**：只有 GitHub 有历史（内置 31 天真实快照），GitLab / Gitee 次日开始出现增量。
- **增量显示 `—`**：该日期没有对应快照，不猜、不插值。
- **⚠ 标记**：单日增量超过昨日存量 30% 且大于 100 星，可能是刷星或推广活动，看榜时留意。
- **重置时间过长**：配额耗尽时程序会跳过该仓库并记日志，不会卡死，已采数据照常落盘。

---

## 五、看板功能

- 五个视图切换：**今日涨星 / 7 日涨星 / 30 日涨星 / 总星榜 / 平台对比**
- **平台对比**：三平台并排展示今日涨星合计、Top 5 项目与横向对比条，快速看清哪个平台今天更热
- 平台筛选：全部 / GitHub / GitLab / Gitee
- 仓库名与描述搜索
- 14 天走势迷你折线：**红涨绿跌**（A 股习惯）
- 顶部统计卡：追踪仓库数、今日最高涨星、快照天数、覆盖平台
- **点击仓库名弹出说明面板**：中文导读（约 160 字，逐条精确翻译的项目功能说明 + 星数规模、增长表现、创建时间、来源渠道）、总星/今日/7 日/30 日增量、走势图，原英文描述折叠可展开，底部一键打开原仓库
- 中文导读不依赖翻译 API、离线可用：`config/desc_zh.json` 存放 250 条逐条核对的中文翻译，覆盖全部英文/中英混合描述；无描述项目基于项目名做保守说明、不臆测功能。星数、时间、语言、增长等事实来自真实快照
- 新增项目若没有对应翻译，会显示"项目自述（原文）"并保留英文原句。想让它也显示中文，在 `config/desc_zh.json` 里按 `"平台:owner/repo": "中文说明"` 加一条即可
- 面板支持点遮罩关闭、右上角 × 关闭、Esc 关闭，关闭后**保持原来的滚动位置**，不回顶部

**看板是完全自包含的单文件**：数据直接内嵌在 `docs/index.html` 里，不依赖 `data/` 文件夹。
手机浏览器、微信、离线、把 HTML 单独发给别人，打开都有数据。每次重新运行会刷新内嵌数据。

数据存在 `data/snapshots/`，是唯一事实来源。想清空重来就删掉这个目录里的 JSON（会失去历史增量）。
