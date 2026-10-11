# data-viz 维护者手册（自己看）

> 适用：你自己维护、迁移、排障这套 skill 时
> 配套：明天对外用的那份是《data-viz 正式分析手册》（偏演示与分析流程）
> 本文档记录**改造细节与内部机制**，包含实现证据、已知缺陷、可移植性说明
> 版本：v3.0（AI 直读 + 用户选单 + 统计分析扩展），改造日期见文件时间戳

---

## 一、这次改了什么（v3）

| 编号 | 改动 | 落地位置 | 验证方式 |
|---|---|---|---|
| 1 | **读数据改为 AI 直接操作**，本地脚本降级为「可选加速器」 | `SKILL.md` §1 | 文档明确「这步需要判断吗」判据；会话 skill 目录已刷新出新描述 |
| 2 | **用户选单机制**：分析意图菜单 + 交付物菜单 + `plan.json` | `SKILL.md` §2.2/§2.3 | 实测：`plan.json` 写入 9 个意图 / 4 类交付物 |
| 3 | **新增 6 种统计图**：`box` `qq` `pareto` `missing` `corr` `regress` | 引擎 Python + 模板 JS + 闸门契约 | 实测看板 21 组件、闸门 A/B/C 全绿、数据逐项核验 |
| 4 | **修掉引擎一个静默数值缺陷**（`_agg_table` 解析值列错误） | `render_universal_dashboard.py` | 修复前帕累托累计占比全 0，修复后 34.91→100% |
| 5 | **可移植性**：清掉全部机器相关绝对路径 | 脚本 + examples | 全仓扫描 0 残留（仅文档示例文字） |
| 6 | 附：`runner.py` 导入 bug 修复（`auto_preview` 不存在 → `scan`） | `scripts/runner.py` | 实测产出 5 件产物 |

---

## 一·补、仓库与版本

- 仓库：**https://github.com/gy-999/data-viz**
- 当前版本：`v3.0`（本次改造已推送，标签 `v3.0`；历史版本 `v2.1` 仅存档）
- 推送方式：git 走 **SSH**（本机 `id_ed25519` 已授权；HTTPS 在本网络下会被重置且无凭证助手）
- 同步装机：`10_scripts/_install_sync.py`（主副本 → Claude Code + DSH，逐文件 MD5 校验）

> **旧版本已废弃**：v2.1 的 17 种图表、`auto_preview` 导入缺陷、机器绝对路径等问题均已由 v3.0 取代；
> 请勿再从旧副本安装。旧手册 `data-viz-使用手册.*` 已删除。

## 二、内部机制：哪一步是 AI、哪一步是代码

这是你最该记住的一张表（也是 v3 的核心变更）：

| 环节 | 执行者 | 依据 |
|---|---|---|
| **读数据**（CSV/Excel/GZ/SQL/JSON/目录） | **AI 直读**（v3 默认） | SKILL.md §1：AI 全量/分块/抽样读入上下文；编码级联是 AI 的读法，不是必须调脚本 |
| 结构速览（超大文件） | 代码（可选） | `scan_preview.scan()`；注意 >50 万行会截断计数 |
| **探源六项** | **AI 亲自推理** | SKILL.md 原文：探源是「AI 心里的清单，**不是要跑的脚本**」 |
| 机械画像（空值率/基数/时间范围） | 代码（可选辅助） | `auto_analyze.py` 提供数字，但**结论由 AI 下** |
| **口径拍板** | **AI 提问 + 用户拍板** | SKILL.md §4：4 步不可跳步，无任何脚本实现 |
| **输出选单** | **AI 念菜单 + 用户选** | v3 新增，落盘为 `plan.json` |
| 看板渲染 | 代码 | `render_universal_dashboard.py` + `_dashboard_template.html` |
| 报告排版 | 代码 | `report_docx.py`（AI 出 spec，代码只排版） |
| 质量闸门 | 代码（硬拦截） | `dashboard_check.py` + `dashboard_contracts.py` |
| 文档/媒体抽取 | 代码 | `doc_extract.py` / `media_probe.py`（纯机械活） |

**判据**：需要判断 → AI 做；纯机械搬运 → 脚本做。

---

## 三、安装与迁移（新机器照做）

```powershell
# 1) 放进 skills 目录（DSH 会自动识别，无需重启）
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.dsh\skills" | Out-Null
Copy-Item "<你的克隆目录>\data-viz" "$env:USERPROFILE\.dsh\skills\data-viz" -Recurse -Force

# 2) 装依赖（用 DSH 自带运行时，别用系统 Python）
$py = "$env:USERPROFILE\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py -m pip install --no-input PyYAML matplotlib pymysql pdfplumber

# 3) 验证三连
& $py -c "import yaml, matplotlib, pymysql, pdfplumber; print('依赖 OK')"
& $py "$env:USERPROFILE\.dsh\skills\data-viz\scripts\media_probe.py" --source "<图片目录>" --json | Select-Object -First 8
```

**依赖清单与用途**

| 包 | 必需性 | 用途 |
|---|---|---|
| PyYAML | **必需** | 看板配置解析（引擎顶层 import，缺了直接起不来）|
| matplotlib | 需要 PNG 图 | `_charts.py`、报告配图 |
| pymysql | MySQL 通路 | `scan_preview` 的 MySQL 分支 |
| pdfplumber | PDF 通路 | `doc_extract.py` |
| pandas / openpyxl / XlsxWriter / python-docx / python-pptx / Pillow / lxml | 已随运行时 | 数据与 Office 处理 |

**选哪个 Python（重要，实测踩过）**

| 解释器 | 版本 | sqlite3 | 依赖 | 结论 |
|---|---|---|---|---|
| DSH 自带运行时 `…\dsh-runtimes\…\python.exe` | 3.12.14 | ✅ 3.53.1 | ✅ 全齐 | **开箱即用，推荐** |
| `D:\Anaconda\python.exe` | 3.9.13 | ❌ `_sqlite3` DLL 缺失 | 已补装 | **不能出看板/报告** |
| `D:\Apps\PyCharm\python interpreter\python.exe` | 3.11.3 | ✅ | 缺全部 | 需自行装依赖 |

- Claude Code 与 DSH 都优先用 **DSH 自带运行时**这个解释器（零安装）。
- Anaconda 那份 Python 的 `sqlite3` 是**发行版本身损坏**（`ImportError: DLL load failed while importing _sqlite3`），
  纯读数据脚本能跑，但看板数仓与报告生成必然失败——**不要试图修 Anaconda，换解释器**。
- 已提供 `requirements.txt`；`SKILL.md` §9 写明了三级解释器选择顺序（`DATA_VIZ_PYTHON` 环境变量 → DSH 运行时 → 系统 python）。

**3 个原版缺陷（本次已修，迁移时注意别被覆盖）**

| # | 原始现象 | 修法 |
|---|---|---|
| 1 | `runner.py` 报 `ImportError: cannot import name 'auto_preview'` | 改成 `from scan_preview import scan` |
| 2 | examples / `build_resource_dashboard.py` 写死作者机器路径（`D:\study\...`） | 统一改为 `Path(__file__).resolve().parent` 相对定位 + 环境变量覆盖 |
| 3 | ODF 案例硬依赖 WELL 案例中间产物 `view_dict.json` | 改为「有则加载，无则警告跳过」|

---

## 四、本次改造的实现细节

### 4.1 新增 6 种统计图（v4）

**引擎侧**（`render_universal_dashboard.py`）：`TYPE_DEFAULTS` 增加 6 项；`build_comp` 增加 6 段载荷构建；空数据自动隐藏检查覆盖新类型。

**统计量全部本地实现，不引入 scipy**：

| 图 | 算法 |
|---|---|
| `box` 箱线图 | 四分位用线性插值（`(n-1)*p`），离群点用 1.5×IQR 栅栏，额外给均值/标准差/变异系数 |
| `qq` 正态Q-Q | 秩→概率 `(i-0.375)/(n+0.25)`，正态分位数用 **Acklam 有理逼近**（误差 < 1.15e-9），并给偏度/峰度 |
| `pareto` 帕累托 | 降序累计占比 + 自动识别 80% 关键少数（返回 `vital_label` / `vital_count`）|
| `missing` 缺失值画像 | 分字段缺失率 + 按维度分组缺失率（双栏，同一张图）|
| `corr` 相关矩阵 | 皮尔逊 / 斯皮尔曼（秩用平均秩法处理并列值）|
| `regress` 回归 | 最小二乘，返回斜率/截距/R² |

**模板侧**（`_dashboard_template.html`）：`RENDERERS` 增加 6 个渲染函数。箱线图用 ECharts `custom` 系列手工绘制（矩形箱体 + 中位线 + 须线 + 离群点散点），Q-Q 用散点 + 参考虚线，相关矩阵复用 heatmap + visualMap。

**闸门侧**（`dashboard_contracts.py`）：`SELECTION_RULES` 增加「数据质量」「组间比较」意图；`TYPE_PREREQUISITES` 增加 6 条前置条件；`check_selection` 增加 6 段选型校验（数值列语义、列数下限、method 白名单等）。

### 4.2 修掉的引擎缺陷（重要）

`_agg_table()` 旧逻辑：

```python
vcol = comp.get("value_col") or (m["source"]["column"] if m else comp.get("metric"))
if vcol not in table_cols(comp["table"]): vcol = comp.get("metric")
```

**缺陷**：当组件自带聚合表、而 metric 的源列不在该表时，`vcol` 会退化成 **metric 的 ID 字符串**（例如 `"sales"`）。SQLite 取字符串常量 → 每行值都是 `"sales"` → 累计占比、总额**静默变成 0**，而图表照画不误（看不出报错）。

**新逻辑**：按 `value_col → 指标源列（同表优先）→ 指标ID → 指标名` 依次探测真实列名，再兜底取「非维度列」。

**影响面**：所有在聚合表上使用 `metric: <指标ID>` 的 `bar` / `pie` / `pareto`。修复后实测：

- 省份帕累托：322,285 → 累计 34.91 / 52.44 / 69.51 / **84.86** → 100%，关键少数 = 四川省
- 折扣档帕累托：311,948 → 关键少数 = 0.2 档
- 饼图 total 与合计口径一致（923,303）

**给配置作者的约定**（已写进 SKILL.md §6.1）：聚合表上的 `metric` 直接写**列名**；若该表没有该列，用 `value_col` 显式指定。

### 4.3 可移植性

- 脚本内一律 `Path(__file__).resolve().parent` 定位自身
- examples 支持环境变量覆盖：`DATA_VIZ_DATA_DIR` / `DATA_VIZ_OUT_DIR`
- 复查结果：全仓 `*.py` / `*.md` 已无机器相关绝对路径（`references/user-interaction-guide.md` 里的 `D:\数据` 是对话示例文字，无需改）

> ⚠️ **教训（我犯过一次）**：为了清理残留路径，我用 `git checkout` 还原渲染引擎，**把刚加的 6 种图表类型一起冲掉了**，而且 `py_compile` 查不出来（类型缺失只在运行时暴露）。所以：
> 1. 改动后**先存补丁**：`git diff > skill-changes.patch`
> 2. 还原前先确认要还原的文件里有没有本次改动
> 3. 验证要**跑行为测试**（`len(TYPE_DEFAULTS)`、闸门、看板数据），不能只做语法检查

---

## 五、界面与契约（改引擎时必须同步的 4 处）

新增一种图表要同时改 4 个地方，缺一处就会被闸门拦或画出空白：

| # | 文件 | 改什么 |
|---|---|---|
| 1 | `render_universal_dashboard.py` | `TYPE_DEFAULTS` 注册类型 + `build_comp` 出载荷 + 空数据检查 |
| 2 | `_dashboard_template.html` | `RENDERERS` 加渲染函数（否则空白）|
| 3 | `dashboard_contracts.py` | `TYPE_PREREQUISITES` + `check_selection`（否则要么无校验、要么未知类型打回）|
| 4 | `SKILL.md` | 图表全集表 + 意图菜单 |

**数仓与命名契约（闸门硬规则）**

- 表名必须是 `ads_*`（面向应用）或 `dwd_*`（明细），否则闸门报「表不存在（可用 ADS 表：…）」
- **任何会被展示的字段都要有中文业务名**，否则闸门以「用户会看到英文原始列名」打回（退出码 2）
- 中文业务名注册在 `render_universal_dashboard.py` 的 `FIELD_CN` / `COL_CN`；临时补录建议用带标记的幂等插入

---

## 六、验证清单（每次改完跑一遍）

```powershell
$py  = "$env:USERPROFILE\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$viz = "$env:USERPROFILE\.dsh\skills\data-viz"

# 1) 语法 + 类型注册
& $py -c "import sys; sys.path.insert(0, r'$viz\scripts'); import render_universal_dashboard as R; \
print('类型数:', len(R.TYPE_DEFAULTS)); print('qnorm(0.975)=', round(R._norm_ppf(0.975),4))"

# 2) 模板 JS 语法（把模板脚本抽出来给 node --check）
& $py -c "import re,pathlib; t=pathlib.Path(r'$viz\scripts\_dashboard_template.html').read_text(encoding='utf-8'); \
pathlib.Path('tpl.js').write_text('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', t, re.S)).replace('__DATA__','{}'), encoding='utf-8')"
& "$env:USERPROFILE\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe" --check tpl.js

# 3) 端到端：跑一个案例，看闸门是否 A/B/C 全绿
& $py "$viz\scripts\render_universal_dashboard.py" "<案例目录>"
& $py "$viz\scripts\dashboard_check.py" "<案例目录>\dashboard.html"
```

**今天实测的通过标准（可作为回归基线）**

| 检查 | 期望 |
|---|---|
| 类型数 | 23 |
| qnorm(0.975) | 1.96 |
| 模板 JS | `node --check` 通过 |
| 看板渲染 | `21 组件 / 警告 0 条` |
| 闸门 | A/B/C 全绿、0 回归 |
| 帕累托累计占比 | 末项 = 100.00，关键少数非空 |
| 报告 DOCX | 结构校验 `verdict: pass` |

---

## 七、已知缺陷与遗留项

| 项 | 现状 | 建议 |
|---|---|---|
| `scan_preview.py` >50 万行截断计数 | 实测 60 万行文件报 `rows: 500001` | 已知行为；大文件走 AI 直读或分块脚本 |
| `runner.py` 只分析前 15 行预览 | 实测 2000 行 CSV 报 `rows: 15` | 已在 SKILL.md 标注「只能做结构体检」；可考虑改成可配置 `--preview-rows` |
| `example_*_pipeline.py` 需要作者内网数据 | `D:\数据\ZJsftp\...` 不存在 | 已参数化 + 占位符；当模板读 |
| `corr` 只支持两两完整样本 | 缺行会被整行丢弃（listwise） | 若要 pairwise，需另加参数 |
| 箱线图 y 轴用归一化坐标 | 数值轴隐藏，靠 tooltip 读值 | 视觉简洁但无法直接读轴刻度；如需真实刻度要改渲染 |
| 模板 `__DATA__` 注入 | 单文件体积随数据增大（当前 1.15 MB）| 大表下钻建议限制 `l3.limit` |

---

## 八、文件清单与职责

| 文件 | 职责 | v3 是否改动 |
|---|---|---|
| `SKILL.md` | 给 AI 的行为规范（含选单、判据、契约）| ✅ 重写 |
| `scripts/render_universal_dashboard.py` | 看板渲染引擎（23 种组件）| ✅ 扩展 + 缺陷修复 |
| `scripts/_dashboard_template.html` | 前端模板（ECharts 渲染器）| ✅ 加 6 个渲染器 |
| `scripts/dashboard_contracts.py` | 选型规则 + 数据字典 + 生成闸门 | ✅ 注册新类型 |
| `scripts/dashboard_check.py` | 看板 A/B/C 回归检查 | — |
| `scripts/report_docx.py` | 数据总结报告排版 | — |
| `scripts/report_gen.py` / `_charts.py` | Excel / Markdown / PNG 交付 | — |
| `scripts/media_probe.py` | 媒体资产盘点 + 重复检测 | — |
| `scripts/doc_extract.py` | Word/PPT/PDF 抽取 | — |
| `scripts/scan_preview.py` / `runner.py` | 可选：结构速览 / 结构体检 | runner 修 bug |
| `scripts/sql_parser.py` | SQL 脚本提数据行 | — |
| `examples/*.py` | 端到端案例（当模板）| ✅ 参数化 + 可移植 |

**改动留存**：本次全部改动已存为补丁 `_internal/patches/skill-v3-changes.patch`，已同步到 Claude Code 与 DSH 两个平台（各 33 个文件，哈希一致）。
