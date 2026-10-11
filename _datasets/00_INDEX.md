# 入口索引 · data-viz 实训资料

> 这个目录用于**试跑与验收 data-viz skill**。内容 = 公开数据集 + 你本机媒体资产 + 两份手册 + 一次完整实测的产物。
> 体积约 390 MB（其中 297 MB 是本机媒体资产，可随时删）。
> 命名约定：**编号目录 = 可探索内容**，**下划线目录 = 内部件（缓存/补丁/中间产物）**。

---

## 一、先看什么

| 我想… | 打开 |
|---|---|
| **明天直接发给人看** | [`11_share_ready/`](11_share_ready)（3 个自包含包，含 zip）|
| 明天对外演示（自己讲） | [`00_guides/data-viz-分析手册.docx`](00_guides) |
| 自己维护/排障/迁移 | [`00_guides/data-viz-维护者手册.docx`](00_guides) |
| 直接看看板长什么样 | [`11_share_ready/1_订单数据分析/dashboard.html`](11_share_ready)（双击即开） |
| 看这次实测的完整结论 | [`11_share_ready/1_订单数据分析/数据总结报告.docx`](11_share_ready) |
| 拿 skill 源码 | **https://github.com/gy-999/data-viz** |
| 验收 skill 有没有真发现问题 | [`00_expected-findings.md`](00_expected-findings.md) |
| 查每份数据的来源与用途 | [`manifest.csv`](manifest.csv) |

---

## 二、目录结构

```
_datasets/
├── 00_INDEX.md              ← 你在这里
├── 00_expected-findings.md  ← 验收基准（实测算出来的异常数字）
├── manifest.csv             ← 数据来源清单
├── 00_guides/               ← 两份手册（.md 源稿 + .docx 成品）
├── 01_public_csv/           ← 7 张公开 CSV（最小闭环）
├── 02_multitable/           ← MovieLens 四表（多源合并）
├── 03_text_dirty/           ← 银行营销 + 超级商店 + 中文 GBK 订单表（数据质量）
├── 04_media_inventory/      ← 本机图片/视频/文档/压缩包（资产盘点 + 重复检测）
├── 05_geo_time/             ← USGS 地震 + 西雅图气温 + 全国行政区划码表
├── 06_excel/                ← 微软官方 Financial Sample（真 xlsx）
├── 07_sql/                  ← Chinook 建表 + INSERT 脚本
├── 08_large/                ← 60 万行订单大表（含时间悬崖）
├── 09_dashboards/           ← 全部看板与报告（源目录）
├── 10_scripts/              ← 复现/装机/分享包脚本
├── 11_share_ready/          ← **明天要分享的三个自包含包（含 zip）**
└── _internal/               ← _raw 缓存、output 中间产物、patches 补丁
```

## 二·补、明天要分享的三个包

每个包都是**自包含**的：一个文件夹（＋同名 zip），里面有看板、报告、配置、数仓，还有一份 `README.md` 说明怎么打开。发出去对方双击 HTML 就能看，不需要联网、不需要装软件。

| 包 | 内容 | zip |
|---|---|---|
| [`1_订单数据分析`](11_share_ready) | 看板（21 组件/6 种新统计图）+ Word 总结报告 + 口径卡 + 输出选单 + 数仓 | 0.75 MB |
| [`2_WELL看板演示`](11_share_ready) | WELL 测试看板（16 组件）+ 配置 + 数仓 + 口径卡 | 0.73 MB |
| [`3_ODF看板演示`](11_share_ready) | ODF 测试看板（11 组件）+ 配置 + 数仓 + 口径卡 | 0.57 MB |

> 前两个演示包由官方案例模板 + 合成数据生成，用于展示产出形态，**不是真实业务结论**；`1_订单数据分析` 基于 `03_text_dirty/chinese_orders_gbk.csv`，是完整分析（结论见分析手册第七节）。

## 二·补二、仓库与分享链接

| 用途 | 链接 |
|---|---|
| 源码仓库 | **https://github.com/gy-999/data-viz** |
| 直接下载 zip | https://codeload.github.com/gy-999/data-viz/zip/refs/heads/main |
| 版本标签 v3.0 | https://github.com/gy-999/data-viz/releases/tag/v3.0 |


## 三、八条通路各练什么

| 目录 | 内容 | 规模 | 训练目标 |
|---|---|---|---|
| `01_public_csv` | tips / flights / iris / penguins / gapminder / titanic / diamonds | 最大 5.4 万行 | 最小闭环：探源 → 口径 → 看板 → 报告 |
| `02_multitable` | MovieLens 四表（ratings / movies / links / tags） | 10 万评分 | 多源合并、跨表关联 |
| `03_text_dirty` | 银行营销（分号分隔）＋ 超级商店（行长不齐）＋ **中文 GBK 订单表** | 最大 4.1 万行 | 编码级联、伪装缺失、哨兵值、坏行 |
| `04_media_inventory` | 本机 137 图 + 10 视频 + 18 文档 + 14 压缩包（**含 18 组重复图**） | 176 文件 / 297 MB | 资产画像、重复图检测、文档抽取 |
| `05_geo_time` | USGS 2024 地震 + 西雅图 1948 起气温 + 全国行政区划码表 | 地震 1.4 万条 | 经纬度分布、时间序列 |
| `06_excel` | 微软 Financial Sample | 701 × 16 | Excel 通路 |
| `07_sql` | Chinook 音乐库 | 11 张表 | 从 SQL 脚本提数据行 |
| `08_large` | 60 万行订单大表（2025 年只到 3 月＝时间悬崖） | 48 MB | >50 万行自适应 |

## 四、09_dashboards 里有什么

| 子目录 | 内容 | 来源 |
|---|---|---|
| `well/` | WELL 测试看板（1.09 MB，16 组件，闸门全绿）＋数仓＋配置＋口径卡 | 官方案例模板 + 合成数据 |
| `odf/` | ODF 测试看板（1.09 MB，11 组件，闸门通过）＋同上 | 官方案例模板 + 合成数据 |
| **`chinese_orders/`** | **本次实测**：看板 1.15 MB（21 组件，含 6 种新统计图）＋`数据总结报告.docx`＋口径卡＋`plan.json`＋数仓 | 你的中文 GBK 订单表 |

> `well/` 与 `odf/` 是用官方案例模板跑通的演示，用于说明产出形态，**不是真实业务结论**；`chinese_orders/` 是基于 `03_text_dirty/chinese_orders_gbk.csv` 的完整分析（结论见分析手册第七节）。
> `_probe/` 子目录存放探源中间结果（`probe_result.json`）。

## 五、看板怎么用

双击 HTML 即可，浏览器打开，**不需要联网、不需要装任何软件**（图表库已内嵌）。可演示的交互：
KPI 卡悬停看口径（分子/分母）→ 点图表 L2 下钻 → 再点 L3 到逐条明细 → 底部码值字典把 `1/2/3` 翻成业务中文。

## 六、10_scripts 里的脚本

> 下表路径均相对 `10_scripts/`；探源中间结果在 `09_dashboards/_probe/`。

| 脚本 | 用途 |
|---|---|
| `_install_sync.py` | **把 skill 同步安装到 Claude Code 与 DSH**，并逐文件校验（`--dry-run` / `--verify`）|
| `run_01_probe.py` / `run_02_dashboard_v3.py` / `run_03_report.py` | 本次实测三步：探源 → 看板 → Word 报告（可复跑）|
| `_apply_v3_engine.py` + `_v3_builders.py` | 把 v3 引擎改造重新应用到 skill（幂等，防被 checkout 冲掉）|
| `_fetch.ps1` / `_fetch2.ps1` | 重新抓取公开数据集（多镜像回退 + 超时保护）|
| `_build_inventory.ps1` | 重建本机媒体清单（含重复检测）|
| `_organize.py` / `_verify_findings.py` | 分类整理 / 重算探源结论 |
| `_md_to_docx.py` | Markdown → Word（改完手册重新生成用）|

## 七、快速上手（三句对话）

```text
帮我看看 D:\Claude cade\data\_datasets\01_public_csv\gapminder.csv，出一份带看板的数据分析
分析 D:\Claude cade\data\_datasets\03_text_dirty\chinese_orders_gbk.csv，先告诉我这份数据有什么问题
盘点 D:\Claude cade\data\_datasets\04_media_inventory 这个目录，找出重复图片
```

## 八、已知边界（实测）

- `runner.py` 只分析**前 15 行预览**，适合结构体检，**不用于正式分析**。
- `scan_preview.py` 对超过 **50 万行**的文件会截断计数（60 万行文件报 `rows: 500001`）。
- `example_*_pipeline.py` 需要原作者的业务分片数据，只能当**配置模板**读。
- `04_media_inventory/archives` 里是从你机器拷来的 zip（含 Node 工具链压缩包），只是**盘点对象**，不要解开运行。

## 九、来源与许可

| 数据 | 来源 | 许可 |
|---|---|---|
| MovieLens ml-latest-small | GroupLens / 明尼苏达大学 | 自由使用（非商用）|
| USGS 地震 | earthquake.usgs.gov 公开 API | 美国政府公开数据 |
| 微软 Financial Sample | Microsoft 官方示例 | 示例用途 |
| Chinook 数据库脚本 | github.com/lerocha/chinook-database | MIT |
| seaborn-data（tips/flights/iris/penguins/diamonds/taxis）| github.com/mwaskom/seaborn-data | BSD-3 |
| plotly datasets（gapminder/weather 等）| github.com/plotly/datasets | MIT/CC |
| 超级商店订单表 | github.com/leonism/sample-superstore | 示例数据 |
| 银行营销 | UCI ML Repository（经镜像）| CC BY 4.0 |
| 全国行政区划码表 | github.com/modood/Administrative-divisions-of-China | MIT |
| 泰坦尼克 | github.com/datasciencedojo/datasets | 公开 |
| `04_media_inventory` | **你本机**（`D:\Claude cade`、Downloads、Documents）| 你自己的文件 |
| `08_large`、`chinese_orders_gbk.csv` | 本地生成（基于上表改写）| 同上 |
