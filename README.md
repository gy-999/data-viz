# data-viz · 数据可视化统计整理 Skill

**丢给它一份数据（Excel / CSV / GZ / SQL 脚本 / MySQL / 目录），它还你一套可转发的完整交付：数据质量报告 + 中文可读交互看板 + Word / Excel / Markdown 报告 + 口径卡，全程有闸门把关、数字可追溯。**

**Give it any data source, it returns a shareable deliverable set: data-quality report + interactive Chinese-readable dashboard + Word/Excel/Markdown report + metric caliber cards — gated, reproducible, traceable.**

> 已在 3 个真实数据集上端到端验证：MySQL 213 表 / 140 万行 CSV.GZ / 300MB SQL 脚本 / 4 万行 ODF。

## 它做了什么 | What It Does

1. **扫描与探源** — 自动识别 6 种数据源，探源六项（空值率含空串、枚举越界、重复 ID、时间悬崖、孤儿外键、跨表重名），实测抓出过官方字典之外的脏码值
   **Scan & profile** — 6 source types, 6 mandatory quality checks (empty-string nulls, enum overflow, dup IDs, time cliffs…)
2. **口径拍板** — 每个指标一张口径卡：分子/分母/只算什么/不算什么，AI 拿真实数据举例确认，消灭“同名不同数”
   **Caliber cards** — numerator/denominator per metric, confirmed against real data
3. **中文可读看板** — 单文件离线 HTML：五段式 KPI 卡（口径悬停）、饼/条/表等组件、码值字典表、L2→L3 下钻到逐条明细，图例全部翻译成业务中文，普通人看得懂
   **Readable dashboard** — single-file offline HTML, five-section KPI cards with caliber hover, code-value dictionary, drill-down to raw rows
4. **三件套报告** — Word（可微信直发）+ Excel（原生图表）+ Markdown，外加 PNG 静态图
   **Report trio** — Word / Excel / Markdown plus PNG charts
5. **闸门把关** — 18 项生成硬校验 + A/B/C 回归检查，展示字段必须有中文业务名，不通过拒绝出图
   **Generation gates** — 18 hard checks + A/B/C regression, refuse to render without Chinese labels

## 快速开始 | Quick Start

把整个文件夹复制到你的 AI 助手 skills 目录（Claude Code / DSH 等），然后对话：

Copy this folder into your agent's skills directory, then just say:

```text
你："帮我看一下 D:/数据 里有什么数据"
你："分析一下 MySQL 的 cqcc 库，sa_label 表有什么问题"
你："统计 sa_label 的状态分布并出图，我要发给别人看"
```

依赖 | Dependencies：pandas / openpyxl / XlsxWriter / matplotlib / pymysql（pip install pymysql matplotlib）、ECharts 已内嵌离线包。

## 输出全览 | Outputs

| 输出物 | 说明 |
|---|---|
| 数据质量报告 | 探源六项：空值率(含空串)/枚举/重复/时间悬崖/孤儿外键/跨表重名 |
| 源版整理 source-cleaned/ | 清洗后结构化副本（表头=英文名+官方中文名）|
| warehouse.db | SQLite 数仓：明细抽样 + ADS 聚合表 |
| 口径卡 caliber-cards.md | 每个指标的分子/分母/只算/不算，业务方签名栏 |
| 交互看板 dashboard.html | 单文件离线；KPI 口径悬停；L2 维度分解 → L3 逐条明细；码值字典 |
| Word/Excel/Markdown 报告 | 三件套 + PNG 静态图，附“转发说明”教收件人使用 |

## 12 步流程 | Pipeline

```text
确认来源 → 全源发现 → 扫描预览 → 探源六项 → 源版整理 → 业务语义
  → 口径拍板(4步) → 图表选型 → 自动分析 → 三件套输出 → 验证闸门 → 交付九问
```

## 目录结构 | Layout

```text
data-viz/
├── SKILL.md                 # 触发规则 + 12 步框架 + 3 原则 + 安全约束
├── references/              # 图表选型 / 数据质量规则 / 性能策略 / 报告模板…
├── assets/                  # 口径卡模板 / 九问检查单
├── scripts/                 # 扫描 / SQL解析 / 分析 / 渲染引擎 / 闸门
│   └── vendor/echarts.min.js
├── examples/                # 端到端案例管线（WELL / ODF / 快速上手）
└── evals/evals.json         # 测试用例
```

## 设计原则 | Principles

- **先看原始数据**：分析前先呈现数据本来的样子
- **输出可追溯**：每个数字能回溯到来源、清洗步骤与口径卡
- **数据量自适应**：<10 万行全量；10-100 万行分块统计+抽样绘图；GB 级先抽样预览再全量
- **安全第一**：源库只读、密码不进上下文、探完断开、聚合展示

## 致谢 | Credits

- 看板渲染引擎（render_universal_dashboard.py / _dashboard_template.html / dashboard_check.py / dashboard_contracts.py / echarts.min.js）来自 **[dsh-dashboard-ai](https://github.com/33Wade333/dsh-dashboard-ai)**（MIT），本项目按其设计系统产出看板并补充了数据字典闸门用法；
- 口径卡与探源方法论参考 **[data-model-builder](https://github.com/33Wade333/data-model-builder)**（MIT）；
- 感谢两个项目的作者，本 skill 是“语义层建模 → 口径统一 → 一键出看板”链路中**面向已有数据快速体检与交付**的一环。

## License | 许可证

MIT。第三方组件许可见 NOTICE。