# 图表选型指南

> 来源：dsh-dashboard-ai (DDI) 17 组件 + 三层选型逻辑 + alirezarezvani/statistical-analyst 的选型理性
> 数据形态决定图表类型，图表类型决定布局权重

## 三层选型逻辑

用户说"出个图"时，按此顺序决策：

### 第一层：意图路由（问一句/读口径卡）

| 用户想表达的意思 | 推荐组件 type |
|---|---|
| "这个数字是多少"（单值，无目标） | `kpi` |
| "达标了没有"（值 vs 目标） | `bullet`（多指标并排） |
| "趋势怎么样"（随时间变化） | `line` |
| "占比是什么"（静态构成） | `pie`（≤5 块） |
| "占比怎么变"（构成随时间） | `area_stack` |
| "哪个最大"（对比/排名） | `bar` |
| "分布怎么样"（数值分布） | `histogram` |
| "哪两个维度交叉看" | `heatmap` |
| "相关性怎么样"（两数值列） | `scatter` |
| "转化率怎么样"（漏斗） | `funnel` |
| "明细给我看" | `table` |

### 第二层：形态检查（查完数据再定）

| 检查项 | 判断条件 | 影响决策 |
|---|---|---|
| 有无时间列 | 无 → 不能选 line/area_stack | 降级为 bar/table |
| 类别数 | >5 块 → 自动合并"其他"+警告 | pie/bar 可用 |
| 有无目标值 | 有 → bullet 优于 kpi | 优先 bullet |
| 长表指标 | source 带 key → 进热力需显式 column | 提醒用户 |
| 数值列数量 | 2 个数值列 → 可选 scatter | hist 不行 |

### 第三层：硬约束（渲染器自动执行，AI 生成时也要遵守）

1. **饼图 ≤ 5 块**（超出自动合并"其他"+警告）
2. **折线仅限时间轴**（无 time 配置的别放 line）
3. **条形优于饼做精确对比**
4. **热力矩阵适合二维交叉**
5. **禁 3D**；不截断坐标轴；量级悬殊别同轴
6. **未知 type 报错**；x+w>24 自动收窄；坐标重叠自动挪位（警告）
7. **排行/热力表按编号存储时必须声明 order**（如 heat_score DESC）
8. **末年不完整必须 kpi_at**（取最后一个完整年/月）
9. **率列 0-1 小数渲染器自适应**（列名含 rate/pct/ratio/share 且值域≤1）
10. **看板填满一页**：每域 ≥5 组件且网格总行高 ≥7 行。某域撑不起时合并小业务成一域，或补组件

## 默认宽高（24 列网格）

| type | 默认宽 | 默认高 |
|---|---|---|
| kpi | 6 | 5 |
| line | 16 | 6 |
| bar | 8 | 6 |
| pie | 8 | 8 |
| heatmap | 24 | 10 |
| table | 24 | 9 |
| histogram | 12 | 6 |
| funnel | 16 | 6 |
| bullet | 8 | 5 |
| area_stack | 16 | 6 |
| scatter | 12 | 6 |
| waterfall | 16 | 7 |
| sankey | 16 | 8 |
| radar | 8 | 7 |
| gauge | 8 | 5 |
| text | 24 | 2 |
| heading | 24 | 1 |

## 布局规则

- **自动行装满（FCFS）**：省略 grid 时按声明顺序首次适应宽切行，行内按比例刚好填满 24 列，行高自动对齐
- **KPI 连续分组等分**：连续声明 kpi 自动等分行宽，4 张→各 6 列
- **首选宽**：kpi 6、line 16、bar 8、pie/histogram 12、heatmap/table/heading 24——常用组合 line+bar、pie+histogram 刚好满行
- **禁止重叠**（网格互斥）；分区用 heading 不用布局容器
- **对话改图**："把饼图换成条形"→`type: pie→bar`；"趋势图放左边放大"→`grid: {x:0, w:16}`

## 渲染命令

```bash
python scripts/render_echarts_html.py <case_dir> [--config 路径] [--output 路径]
```

输出：单文件 HTML，ECharts 内嵌离线，组件画布 + L2/L3 下钻 + 口径角标
