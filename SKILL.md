---
name: data-viz
description: >
  "帮我看看这些数据" → AI 亲自当分析师兼读取器：AI 直接读数据、边看边推理、拿真实数据向你提问、
  给出结论与洞察；本地脚本只是可选加速器，不是必经管线。支持 6 种数据源（CSV/TSV/GZCSV/Excel/SQL脚本/MySQL）
  + 图片/视频/Word/PPT/PDF 资产盘点，大数据量自适应（小数据 AI 全量直读，大数据一次性片段），多源混合。
  探源与口径拍板之后，先给你一份**输出选单**（出哪些图、哪些交付物），你选完才写代码；
  代码只用于两处：可视化看板（23 种图表，含箱线图/正态Q-Q/帕累托/缺失值画像/相关矩阵/回归）
  与交付报告（Word/Excel/Markdown/PNG）+ 数据总结报告。
  触发词：数据分析、统计、可视化、帮我看看、数据整理、清洗数据、出报告、生成看板、数据质量、扫描数据、
  对比数据、口径、SQL 脚本、数据库分析、目录扫描、多源分析、大文件、图片、视频、文档、Word 表格、资产盘点、重复图片、
  箱线图、分布、相关性、回归、缺失值、帕累托。
  不触发：建数仓/写 SQL 建表/机器学习建模/代码审查。
risk: safe
date_added: '2026-10-10'
updated: 'v3.0 · AI 直读 + 用户选单 + 统计分析扩展'
---

# data-viz · 数据分析 Agent Skill（v3.0 · AI 直读 + 用户选单）

> **核心哲学：AI 就是分析师，AI 就是读取器。**
> 读数据、探源、判断口径 = **AI 亲自做**（推理，不是调脚本）。
> 代码只在三处出现：① 数据大到 AI 读不动时的分块片段（用完即弃）；② **用户选定的**看板与报告；③ 文档类资产的机械抽取。
> **每份分析必须以数据总结报告.docx 收尾**——没有总结文档的分析不算完成。

---

## 一、读数据：AI 直读为默认（v3 变更）

**默认路径：AI 直接读。** 不跑本地扫描器也能开始分析——本地脚本是**可选加速器**，不是必经管线。

| 量级 | AI 怎么读 |
|---|---|
| < 1 万行 | **AI 全量读入上下文**，逐列看真实值；几乎不写代码 |
| 1 万 ~ 50 万行 | AI 分块读 + 抽样式阅读；必要时写一次性 pandas 片段回答**当下那一个问题**，用完即弃 |
| > 50 万行 / GB 级 | AI 先读头部/抽样确认结构，再写一次性分块聚合脚本；聚合结果**回到 AI 解读**，先征用户确认再全量 |

读的时候按编码级联兜底：`utf-8-sig → utf-8 → gbk → gb18030`；分隔符按首行候选（`| \t , ;`）判定；读不到就**换一种读法再试**，而不是报错停下。

**什么时候才用本地工具（可选，不是默认）**：
- `scan_preview.py` — 文件太大（>50 万行）先要个结构速览；注意它对超过 50 万行的文件会截断计数
- `runner.py` — 想要一份「结构体检」产物；注意它**只分析前 15 行预览**，不能当正式分析
- `doc_extract.py` — Word/PPT/PDF 的表格与正文抽取（机械活，交给代码更划算）
- `media_probe.py` — 图片/视频/压缩包的资产画像与重复检测
- `sql_parser.py` — 大 SQL 脚本里提数据行

> 判断标准：**「这步需要判断吗？」需要判断 → AI 做；纯机械搬运 → 脚本做。**

---

## 二、用户选单：出什么，你说了算（v3 新增）

探源结束后、写代码之前，**必须把菜单念给用户听并等其选择**。不要默认全出，也不要替用户决定。

### 2.1 分析意图菜单（决定放哪些图）

| 意图 | 推荐组件 | 数据形态要求 |
|---|---|---|
| 趋势 | `line` / `area_stack` | 时序列 + 度量 |
| 构成 | `pie` / `bar` | 分类维 + 度量 |
| 排名 | `bar` / `pareto` | 分类维 + 度量 |
| 分布 | `histogram` / **`box`** / **`qq`** | 单个或分组数值列 |
| 组间比较 | **`box`** | 分类维 + 数值列 |
| 相关 | `scatter` / **`corr`** / **`regress`** | ≥2 个数值列 |
| 数据质量 | **`missing`** | 任意表 |
| 交叉 | `heatmap` | 分类维 + ≥2 指标 |
| 明细 | `table` | 任意 |
| 流向 | `funnel` / `sankey` | ≥2 阶段度量 |
| 目标 | `bullet` / `gauge` | 单值 + 目标 |
| 多维对比 | `radar` | 分类维 + ≥3 指标 |
| 关键少数 | **`pareto`** | 分类维 + 度量 |

### 2.2 交付物菜单（决定出什么文件）

| 编号 | 交付物 | 说明 | 默认 |
|---|---|---|---|
| A | 可视化看板 `dashboard.html` | 单文件离线，含 KPI 口径悬停 + L2→L3 下钻 | ✅ 默认要 |
| B | 数据总结报告 `数据总结报告.docx` | 概览/质量/指标/图表/洞察/建议/转发说明 | ✅ **必产** |
| C | 口径卡 `口径卡.md` | 每个指标的分子/分母/只算/不算 | ✅ 默认要 |
| D | Excel 交付 `报告.xlsx` | 带原生图表 | 询问 |
| E | Markdown 摘要 | 便于贴群/进工单 | 询问 |
| F | PNG 静态图 | 贴聊天窗、进 PPT | 询问 |
| G | 数据质量报告 | 缺失/重复/异常值 + 修复建议清单 | 询问 |
| H | 清洗后的数据副本 | 结构化输出，源文件不动 | 询问 |

### 2.3 落盘方式：`plan.json`

用户选完，把选择写成 `plan.json` 放进案例目录，渲染时读取。**用户的显式选择优先于任何默认值。**

```json
{
  "intents": ["趋势", "构成", "排名", "分布", "数据质量"],
  "deliverables": ["A", "B", "C", "G"],
  "extras": { "top_n": 12, "corr_method": "spearman", "box_group": "产品类别" },
  "notes": "用户要求所有分布图必须带离群点标注"
}
```

---

## 三、探源思维（AI 亲自做，不是脚本）

读任何数据源时，主动检查并在发现异常时**拿真实数据问用户**：

- 空值率——**空字符串也算空**（真实脏数据常用 `""` 而非 NULL）；`None`/`NULL`/`999` 这类**哨兵值**要单独识别
- 枚举越界——DISTINCT 列出来，文档说的和实际的对照；含义不明就推断后复述确认
- 重复行——「业务上一件事的边界在哪？」
- 时间范围与悬崖——末年未存满须用同期口径；**同一日期异常堆积**说明数据被压平，时间维度不可用
- 孤儿外键、跨表重名字段
- 编码——级联兜底，别在第一步就失败

## 四、口径拍板（4 步，不可跳步）

1. 用户口述指标含义 2. AI 拿真实数据举例确认（「这 48.6% 没支付的算分母吗？」）3. 沉淀口径卡（分子/分母/只算/不算/更新周期）4. 实现
- 口径跨指标复用必须重新确认；用户说「你定吧」=委托，定完必须告知并留痕
- **每个 KPI 卡都要能悬停看到口径**，否则闸门不算通过

## 五、码值翻译

图例里的 `1/2/3` 码值必须翻译：先查官方字典（建表 COMMENT / 视图文档），查不到就推断并标注「待确认」，用户确认后生效。

## 六、用户拍板之后：代码登场

1. **看板** — AI 写 `dashboard.config.yaml`（声明式），渲染引擎输出单文件离线 HTML；`plan.json` 决定放哪些组件
   ```bash
   python scripts/render_universal_dashboard.py <案例目录>   # 闸门自动校验，不通过拒绝出图
   ```
2. **数据总结报告（必产）** — AI 写叙事与结论 spec（概览/质量/指标/图表/洞察/建议/转发说明），`report_docx.py` 只做排版
3. **质量闸门** — `dashboard_check.py` A/B/C 回归 + `dashboard_contracts.py` 选型校验 + **展示字段必须有中文业务名**（否则打回，退出码 2）

### 6.1 看板配置最小示例

```yaml
version: 2
title: 订单分析看板
time: { table: ads_trend, column: 月份 }        # 折线图必须：全局时间轴
metrics:
  - id: sales                                 # 指标 ID，供 KPI / line 引用
    name: 销售额合计
    unit: 元
    direction: up
    caliber: 销售额合计                         # 对应 artifacts/口径卡.md 里的指标名（KPI 悬停显示口径）
    source: { table: ads_overview, column: 值, key: { 指标: 销售额合计 } }
components:
  - { id: k1, type: kpi, metric: sales }
  - { id: l1, type: line, metrics: [monthly_sales] }        # 时间序列：metrics 必须是"指标ID"列表
  - { id: p1, type: pie, metric: 销售额, table: ads_category, dimension: 维度, order: 销售额 DESC }
  #      ↑ 聚合表里的 metric 直接写"列名"；本表没有该列时用 value_col 显式指定
  - { id: b1, type: box, table: dwd_orders, dimension: 产品类别, column: 销售额 }
  - { id: c1, type: corr, table: dwd_orders, columns: [销售额, 数量, 折扣, 利润], method: spearman }
  - { id: m1, type: missing, table: dwd_orders, dimension: 产品类别, col_top: 12 }
drill:
  l2: { dimensions: [ { table: ads_category, dimension: 维度, order: 销售额 DESC } ] }
  l3: { table: dwd_orders, columns: [订单号, 订单日期, 销售额, 利润], limit: 200 }
```

**数仓表名必须用 `ads_*` / `dwd_*` 前缀**（ADS 面向应用、DWD 明细），否则闸门直接打回。
**每个会被展示的字段都要有中文业务名**，否则闸门以「用户会看到英文原始列名」为由打回（退出码 2）。



| 类别 | 类型 |
|---|---|
| 指标 / 文本 | `kpi` `text` `heading` |
| 趋势 / 构成 | `line` `area_stack` `bar` `pie` `histogram` |
| 关系 / 流向 | `scatter` `heatmap` `funnel` `sankey` `waterfall` |
| 对比 / 目标 | `radar` `gauge` `bullet` `table` |
| **统计分析（v4 新增）** | **`box`**（箱线图·四分位+离群点） **`qq`**（正态Q-Q·偏度峰度） **`pareto`**（帕累托·80/20 关键少数） **`missing`**（缺失值画像） **`corr`**（相关矩阵·皮尔逊/斯皮尔曼） **`regress`**（回归·斜率截距 R²） |

> 统计量由引擎本地计算（不依赖 scipy）：四分位用线性插值、离群点用 1.5×IQR、正态分位数用 Acklam 逼近、斯皮尔曼用平均秩。

## 七、scripts/ 工具箱

| 工具 | 什么时候用 |
|---|---|
| `render_universal_dashboard.py` + `vendor/` | 看板渲染引擎 + 离线 ECharts（23 种组件）|
| `dashboard_check.py` / `dashboard_contracts.py` | 看板质量闸门 / 选型规则 + 数据字典 |
| `report_docx.py` | 数据总结报告排版（AI 出 spec，代码只排版）|
| `report_gen.py` / `_charts.py` | Excel / Markdown / PNG 交付 |
| `media_probe.py` | 图片/视频/压缩包资产盘点（EXIF、重复图、文件族）|
| `doc_extract.py` | Word/PPT/PDF 表格→CSV、正文→fulltext |
| `sql_parser.py` | 大 SQL 脚本提数据行（bulk INSERT）|
| `scan_preview.py` | 超大文件/目录速览（**可选**；>50 万行会截断计数）|
| `runner.py` | 结构体检管线（**可选**；只分析前 15 行预览）|

## 八、三类真实场景的处理策略

| 场景 | 数据形态 | AI 该做什么 | 产出 |
|---|---|---|---|
| 代码/学习资料项目 | 数千图片 + SQL 脚本 + PDF + 代码 | `media_probe` 资产盘点+重复检测；SQL 批量解析；PDF 正文提取；**代码本身不审查（边界）** | 资产盘点报告.docx（重复清单=清理依据）|
| 项目文档集 | 需求书/手册 docx + 测试追踪 xlsx + 视频 | `doc_extract` 表格→CSV 进分析管线；追踪表全管线分析 | 文档集盘点报告.docx |
| 业务分片数据 | 官方视图字典配套的分片 CSV | 全流程：AI 直读→探源→码值字典翻译→口径拍板→看板→总结报告 | 业务看板 + 总结报告.docx |

## 九、运行环境（Python）

本 skill 的脚本是**普通 Python 脚本**，任何 3.9+ 解释器都能跑，但有两条前置检查：

```bash
# 1) 依赖（PyYAML 是硬依赖，缺了渲染引擎直接起不来）
<python> -m pip install -r requirements.txt

# 2) 标准库 sqlite3 必须可用（看板数仓与报告依赖）
<python> -c "import sqlite3; print(sqlite3.sqlite_version)"
```

**选择解释器的顺序（DSH 与 Claude Code 都适用）**：

1. 环境变量 `DATA_VIZ_PYTHON` 指定的解释器；
2. DSH 自带运行时（**无需额外安装依赖，开箱即用**）：
   `%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`
3. 系统 `python` / `py -3`，并按上面的命令补装依赖。

> **实测坑**：部分发行版（如某些 Anaconda 安装）的 `sqlite3` 会因缺少 `_sqlite3` DLL 而**完全不可用**
> （报 `ImportError: DLL load failed while importing _sqlite3`）。这类解释器能跑纯读数据，
> 但**无法生成看板与报告**——遇到时换用第 2 项的解释器，不要试图修 Anaconda。

## 十、安全与可移植性约束

- 源数据库只读 `SELECT`；密码不进上下文；探完断开
- **不修改源文件**；输出写工作区的 `output/`（或用户指定目录）
- 大文件先抽样预览，用户确认后再全量
- **路径必须可移植**：脚本内用 `Path(__file__).resolve().parent` 定位自身，禁止写死某台机器的绝对路径；案例数据目录用参数传入（`--data-dir` / `--out-dir`）
- 依赖缺失时给出**明确的安装命令**，不要静默失败

详见 `references/`（数据源策略 / 图表选型 / 质量规则 / 性能策略 / 报告模板 / 交互指南）。
