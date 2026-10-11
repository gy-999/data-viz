---
name: data-viz
description: "帮我看看这些数据" → AI 亲自当分析师。丢给它一份数据（CSV/TSV/GZ压缩/Excel/SQL脚本/MySQL/JSON/图片/视频/Word/PPT/PDF），它直接读数据、边看边推理、拿真实数据向你提问、给出结论与洞察；你拍板口径之后才写代码，且代码只用于可视化看板与交付报告（Word/Excel/Markdown + 数据总结报告）。探源六项、码值字典自动翻译、口径卡、生成闸门、媒体资产盘点、重复图检测一应俱全。13 组真实数据全 PASS，最大 175 万行。触发词：数据分析、统计、可视化、帮我看看、数据整理、出报告、生成看板、数据质量、口径、资产盘点。不触发：建数仓/建模/代码审查。
---

# data-viz · 数据分析 Agent Skill

**v3.0 · AI 直读 + 用户选单 + 统计分析扩展**

**AI 亲自当分析师兼读取器：丢给它一份数据，它还你一套能直接转发的东西。**

**Give it any data — the AI reads it directly, reasons, questions you with real numbers, and returns a shareable deliverable set: interactive dashboard + summary report (Word) + caliber cards, all gated.**

> 已在 **13 组真实与公开数据**上端到端验证：从 304 行的定向脏数据到 **175 万行**业务分片，7 种输入通路全部通过，测试逼出并修复 4 个真实缺陷。
> v3.0 新增：AI 直读为默认读法、输出选单（选图选交付物）、6 种统计分析图（共 **23 种**）。

## v3.0 更新 | What's New

| 更新 | 内容 |
|---|---|
| **读数据改为 AI 直接操作** | AI 全量/分块/抽样读入上下文并逐列查看真实值；本地脚本降级为「可选加速器」，不再是必经管线 |
| **输出选单** | 探源与口径拍板后，先给分析意图菜单与交付物菜单，选择写入 `plan.json` 再生效 |
| **统计分析扩展** | 新增箱线图、正态 Q-Q、帕累托、缺失值画像、相关矩阵、回归；图表类型达 **23 种** |
| **运行环境说明** | 新增 `requirements.txt` 与 SKILL.md §9：三级解释器选择顺序、sqlite3 自检（避开损坏的 Python 发行版）|
| **可移植性** | 清除全部机器相关绝对路径，改用 `Path(__file__)` 相对定位 + 环境变量覆盖 |

## 它做了什么 | What It Does

1. **AI 亲自当分析师** — 直接读数据、边看边推理、拿真实数据向你提问（"这 48.6% 没支付的算分母吗？"）。不是跑预写脚本——脚本只在大数据算不动时临时写，用完即弃。
   **AI is the analyst** — reads data directly, reasons interactively, questions you with real numbers. Scripts are throwaway, written only when data is too big to eyeball.
2. **探源六项 + 码值自动翻译** — 空值率（含空串）、枚举越界、重复行、时间悬崖、孤儿外键、跨表重名。图例里的 1/2/3 码值自动从官方字典翻译成业务中文（实测抓出官方字典之外的"码7"越界）。
   **Profiling** — nulls (incl. empty strings), enum overflow, dups, time cliffs, orphan FKs; code values auto-translated from official dictionaries.
3. **口径拍板** — 每个指标一张口径卡：分子/分母/只算什么/不算什么，AI 拿真实数据举例确认，业务方签名生效——消灭"同名不同数"。
   **Caliber cards** — numerator/denominator per metric, confirmed against real data before implementation.
4. **中文可读交互看板** — 单文件离线 HTML：五段式 KPI 卡（口径悬停可见分子分母）、**23 种图表**（含箱线图/正态Q-Q/帕累托/缺失值画像/相关矩阵/回归）、24 列自动布局、L2→L3 下钻到逐条明细、码值字典表、生成闸门（展示字段没有中文名就拒绝渲染）。
   **Readable dashboard** — single-file offline HTML with 5-section KPI cards, caliber hover, L2/L3 drill-down, code-value dictionary table, generation gates.
5. **数据总结报告必产** — 每份分析以 Word 总结报告收尾（AI 写叙事与结论，代码只排版）：概览 → 质量 → 指标 → 图表 → 洞察 → 建议 → 转发说明。没有总结文档的分析不算完成。
   **Summary report mandatory** — every analysis ends with a Word narrative report; no summary, not done.
6. **媒体与文档盘点** — 图片资产画像（EXIF/重复图检测——实测在 3,749 张中找出 1,390 张重复）、Word/PPT/PDF 表格抽取→CSV（宏文档伪装自动修复）、视频/压缩包文件级盘点。
   **Media & docs** — image profiling w/ duplicate detection (1,390 dups found in the wild), Office table extraction (macro-disguised docx auto-repaired).

## 实测成绩单 | Verified on 13 Datasets

| 数据集 | 规模 | 结果 |
|---|---|---|
| ZJsftp WELL（业务 GZ 分片）| 1,409,711×130 | ✅ 看板：码值自动翻译、下钻、闸门全绿 |
| ZJsftp POLE（业务 GZ 分片）| **1,750,619×122** | ✅ 最大实测；官方第 7 码「空载」字典驱动翻译 |
| ZJsftp OCCP | 141,158×351 | ✅ 12 组件看板 |
| sa_label.sql | 300MB / 1,448,752 INSERT | ✅ 自研解析器 |
| MovieLens 四表 | 100,004 评分 | ✅ 多源合并+关联 |
| MySQL cqcc 直连 | 213 表 / 168 万行 | ✅ 全库扫描 |
| 定向脏数据（GBK）| 304 行 | ✅ 探源六项命中 **6/6** |
| wuyuan 文档集 | 18.5MB 宏docx 等 | ✅ **337 张表格抽出**、宏伪装自动修复 |
| JAVA 资料库 | 5,375 文件 / 3,749 图片 | ✅ **发现 1,390 张重复图** |

## 快速开始 | Quick Start

把文件夹复制到 AI 助手的 skills 目录（DSH：`~/.dsh/skills/`；Claude Code：`~/.claude/skills/`），然后直接对话：

```text
你："帮我看看这些数据"                        → AI 直读 + 探源 + 提问
你："分析这份 MySQL 表，出个能发群里的看板"    → 口径拍板 → 看板 + 总结报告
你："盘点一下这个文件夹，有没有重复图片"       → 资产画像 + 重复清单
```

依赖：pandas / openpyxl / XlsxWriter / matplotlib / pymysql / pdfplumber（pip 安装）；ECharts 已内嵌离线包。

## 量级自适应 | Scale-Adaptive

| 量级 | AI 怎么做 |
|---|---|
| < 1 万行 | 直接读全量，推理为主，几乎不写代码 |
| 1 万~50 万行 | 交互式 pandas 片段，用完即弃 |
| > 50 万行 / GB 级 | 一次性分块脚本 + 抽样预览征确认 |

## 输出全览 | Outputs

| 输出 | 说明 |
|---|---|
| 交互看板 dashboard.html | 单文件离线；KPI 口径悬停；L2→L3 下钻；码值字典表 |
| 数据总结报告.docx | 概览/质量/指标/图表/洞察/建议/转发说明（**必产**）|
| 口径卡 caliber-cards.md | 分子/分母/只算/不算/业务方签名 |
| 源版整理 source-cleaned/ | 清洗后结构化副本 |
| 质量闸门记录 | dashboard_check A/B/C + 18 项生成硬校验 |

## 目录结构 | Layout

```text
data-viz/
├── SKILL.md                 # 触发 + AI 读法 + 输出选单 + 探源清单 + 口径拍板 + 运行环境
├── requirements.txt         # 依赖清单（PyYAML 为硬依赖）
├── references/              # 数据源策略 / 图表选型 / 质量规则 / 性能策略 / 报告模板
├── assets/                  # 口径卡模板 / 九问检查单
├── scripts/                 # 工具箱（渲染引擎 23 组件 / 闸门 / 报告 / 媒体 / 文档 / SQL）
│   └── vendor/echarts.min.js
├── examples/                # 端到端案例（WELL / ODF，需自有数据，可当配置模板）
└── evals/evals.json         # 测试用例
```

## 安装 | Install

把 `data-viz` 文件夹复制到 Agent 的 skills 目录即可（DSH：`~/.dsh/skills/`；Claude Code：`~/.claude/skills/`），然后安装依赖：

```bash
<python> -m pip install -r requirements.txt
<python> -c "import sqlite3; print(sqlite3.sqlite_version)"   # 看板数仓依赖它
```

> 详细的环境选择与常见坑（含损坏的 Python 发行版）见 `SKILL.md` 第 9 节。

## 仓库 | Repository

- 源码：**https://github.com/gy-999/data-viz**
- 直接下载：https://codeload.github.com/gy-999/data-viz/zip/refs/heads/main
- 版本标签：`v3.0`（AI 直读 + 用户选单 + 23 种图表）· `v2.1`（历史版本）

## 致谢 | Credits

- 看板渲染引擎与设计系统来自 **[dsh-dashboard-ai](https://github.com/33Wade333/dsh-dashboard-ai)**（MIT）——24 列网格与生成闸门复用其成熟实现（本仓库在其基础上扩展至 23 种组件）；
- 口径卡与探源方法论参考 **[data-model-builder](https://github.com/33Wade333/data-model-builder)**（MIT）；
- 本 skill 是两者链路（语义建模 → 口径统一 → 一键看板）中的**快速数据体检与交付**一环。

## License

MIT（第三方组件见 NOTICE.md）