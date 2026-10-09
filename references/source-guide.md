# 数据源指南

> data-viz 支持 6 种数据源，运行时自动识别

## 数据源类型速查

| 类型 | 识别方式 | 引擎 | 特殊处理 |
|---|---|---|---|
| CSV | 扩展名 .csv | pandas (read_csv) | 自动检测分隔符、编码 |
| TSV | 扩展名 .tsv | pandas (read_csv, sep='\t') | 自动检测编码 |
| GZCSV | 扩展名 .csv.gz / .csv.gzip | gzip + pandas | 自动解压后再读取 |
| Excel | 扩展名 .xlsx / .xls | openpyxl | 多 Sheet 自动发现 |
| SQL 脚本 | 扩展名 .sql | 自定义 VALUES 解析器 | 支持 INSERT INTO ... VALUES (...), (...); |
| MySQL 数据库 | URL 前缀 mysql:// | pymysql | 只读 SELECT，213 张表全部支持 |

## 编码自动探测

> 借鉴 DMB 案例 9/10：真实数据常用空字符串和混合编码

```
尝试顺序：utf-8-sig → utf-8 → gbk → gb18030
```

## 分隔符自动检测

```
头行各分隔符计数：| > \t > , > ;
取计数最高的一个
```

## 多源混合编排

当输入是一个目录时，`scan_preview.py` 自动：
1. 递归扫描所有文件
2. 按扩展名分组识别类型
3. 同构文件（同字段结构的 CSV）自动 batch concat
4. 异构文件（不同结构）分别处理
5. 产出合并清单报告

## 结构

```
output/<timestamp>/
├── source-cleaned/         # 源版镜像（整理后数据）
│   ├── 01_raw_<表名>.xlsx
│   ├── 02_cleaned_<表名>.xlsx
│   └── 03_source-report.md
├── merged/                 # 多源合并
│   ├── 01_merged_clean.xlsx
│   └── 02_cross_source_stats.xlsx
├── report.xlsx             # 三件套之 Excel
├── dashboard.html          # 三件套之 ECharts 看板
├── summary.md              # 三件套之 Markdown 报告
├── caliber-cards.md         # 口径卡清单
└── cleaning-log.md          # 清洗处理日志
```
