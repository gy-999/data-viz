# 数据源处理策略（三类真实场景）

> 来源：D:/study/JAVA、Desktop/wuyuan、D:/数据/ZJsftp 三处真实数据实测沉淀

## 场景一：代码/学习资料项目（如 D:/study/JAVA，1.5GB / 5375 文件）

| 形态 | 占比 | 处理 | 工具 |
|---|---|---|---|
| 图片（png/jpg/gif）| 2755 张 | media_probe：格式/尺寸/EXIF/横竖比/**重复检测（128 组 1390 张）** | media_probe.py |
| SQL 脚本 | 22 个 | 批量解析（INSERT 行数/状态）| sql_parser.py |
| PDF 文档 | 108 个 | 正文→fulltext.txt、表格→CSV | doc_extract.py（pdfplumber）|
| 压缩包 | 33 个 | 内部清单（数量/类型）| media_probe.py |
| 代码（java/js/html/css）| — | **不做内容审查（边界）**，仅文件级计数 | — |

产出：资产盘点报告.docx（重复资产清单 = 清理依据）

## 场景二：项目文档集（如 wuyuan，858MB / 27 文件）

| 形态 | 处理 | 工具 |
|---|---|---|
| 大 docx（含宏伪装）| 表格→CSV + 正文→fulltext；**宏文档自动修复** | doc_extract.py |
| 测试追踪 xlsx | 合并单元格补全 → 分布/交叉/洞察 → 看板 | openpyxl + auto_analyze 思路 |
| 流程视频 mp4 | 文件级盘点（装 ffmpeg 可抽时长）| media_probe.py |
| 模板组 xlsx | 模板生命周期对比（原版/backup/filled/temp）| doc_extract.py |
| PDF | 正文 + 表格 | doc_extract.py |

产出：文档集盘点报告.docx + 337 张表格 CSV（副产品金矿）

## 场景三：业务 GZ 分片（如 ZJsftp，官方视图字典配套）

全流程已验证：探源六项 → 码值字典驱动翻译（**字典 memo 自动解析码值，如 POLE 的码7=空载**）→ 口径拍板 → 看板 → 总结报告。构建器：build_resource_dashboard.py（POLE/OCCP 已出）。

## 通用纪律

- 每份分析以数据总结报告.docx 收尾（report_docx.py）
- 重复资产/质量异常清单 = 用户可执行的清理依据
- 边界：代码审查、OCR、图像内容识别不做