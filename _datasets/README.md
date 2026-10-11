# data-viz 实训数据集

这是 **data-viz** Skill（<https://github.com/gy-999/data-viz>）的配套实训资料，用于试跑与验收。

> 本目录只收录**经过筛选、适合公开**的内容。你本机的媒体资产与大体积数据不入库，但保留了一键重建脚本。

## 一、先看什么

| 我想… | 打开 |
|---|---|
| **直接发给人看** | `11_share_ready/`（3 个自包含包，含 zip，双击 HTML 即看） |
| 演示时自己讲 | `00_guides/data-viz-分析手册.docx` |
| 维护/排障/迁移 | `00_guides/data-viz-维护者手册.docx` |
| 验收 skill 有没有真发现问题 | `00_expected-findings.md` |
| 查数据来源 | `manifest.csv` |

## 二、目录结构

```
├── 00_INDEX.md              入口索引
├── 00_expected-findings.md  验收基准（实测算出的异常数字）
├── manifest.csv             数据来源清单
├── 00_guides/               两份手册（.md 源稿 + .docx 成品）
├── 01_public_csv/           7 张公开 CSV（tips/flights/iris/penguins/gapminder/titanic/diamonds）
├── 02_multitable/           MovieLens 四表（10 万评分）
├── 03_text_dirty/           银行营销（分号分隔）+ 超级商店（行长不齐）+ 中文 GBK 订单表
├── 05_geo_time/             USGS 2024 地震 + 西雅图 70 年气温 + 全国行政区划码表
├── 06_excel/                微软官方 Financial Sample（真 xlsx）
├── 07_sql/                  Chinook 建表 + INSERT 脚本
├── 09_dashboards/           看板与报告源目录（含本次实测案例）
├── 10_scripts/              复现 / 装机 / 分享包 / 数据整理脚本
└── 11_share_ready/          **明天要分享的三个自包含包**
```

**未入库（本机专有，附重建方式）**

| 目录 | 原因 | 重建方式 |
|---|---|---|
| `04_media_inventory/`（297 MB） | 含使用者本人的视频、项目文档等私有素材 | `10_scripts/_build_inventory.ps1`（扫描指定目录生成图片/视频/文档清单并检测重复） |
| `08_large/`（48 MB） | 大体积生成数据 | `10_scripts/_organize.py`（生成 60 万行含时间悬崖的订单表） |
| `_internal/`（20 MB） | 下载缓存与中间产物，可再生 | `10_scripts/_fetch.ps1` + `_fetch2.ps1` |

## 三、三个分享包

每个包＝一个文件夹（＋同名 zip），自包含：看板 + 报告 + 配置 + 数仓 + 说明。

| 包 | 内容 | zip |
|---|---|---|
| `1_订单数据分析` | 21 组件看板（含 6 种新增统计图）+ Word 总结报告 + 口径卡 + 输出选单 + 数仓 | 0.75 MB |
| `2_WELL看板演示` | WELL 测试看板（16 组件）+ 配置 + 数仓 + 口径卡 | 0.73 MB |
| `3_ODF看板演示` | ODF 测试看板（11 组件）+ 配置 + 数仓 + 口径卡 | 0.57 MB |

## 四、快速上手（三句对话）

```text
帮我看看 01_public_csv/gapminder.csv，出一份带看板的数据分析
分析 03_text_dirty/chinese_orders_gbk.csv，先告诉我这份数据有什么问题
盘点 <某个目录>，找出重复图片
```

## 五、已知边界（实测）

- `runner.py` 只分析**前 15 行预览**，适合结构体检，**不用于正式分析**
- `scan_preview.py` 对超过 **50 万行**的文件会截断计数（60 万行文件报 `rows: 500001`）
- `example_*_pipeline.py` 需要自有业务数据，只能当**配置模板**读

## 六、来源与许可

| 数据 | 来源 | 许可 |
|---|---|---|
| MovieLens ml-latest-small | GroupLens / 明尼苏达大学 | 自由使用（非商用） |
| USGS 地震 | earthquake.usgs.gov 公开 API | 美国政府公开数据 |
| 微软 Financial Sample | Microsoft 官方示例 | 示例用途 |
| Chinook 数据库脚本 | github.com/lerocha/chinook-database | MIT |
| seaborn-data（tips/flights/iris/penguins/diamonds） | github.com/mwaskom/seaborn-data | BSD-3 |
| plotly datasets（gapminder/weather） | github.com/plotly/datasets | MIT/CC |
| 超级商店订单表 | github.com/leonism/sample-superstore | 示例数据 |
| 银行营销 | UCI ML Repository（经镜像） | CC BY 4.0 |
| 全国行政区划码表 | github.com/modood/Administrative-divisions-of-China | MIT |
| 泰坦尼克 | github.com/datasciencedojo/datasets | 公开 |
| `chinese_orders_gbk.csv` | 本地生成（基于上述示例数据改写） | 同上 |
