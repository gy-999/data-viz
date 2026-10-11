"""data-viz 正式测试 · 第 2 步（v3）：按用户选单 plan.json 建看板（含 6 种新统计图）

流程对齐 SKILL.md v3：
  探源(AI 读) -> 口径卡(AI 出内容) -> plan.json(用户选单) -> SQLite 数仓 -> dashboard.config.yaml -> 渲染 -> 闸门
数据：03_text_dirty/chinese_orders_gbk.csv（GBK / 4000 行 / 中文表头）
"""
import json
import pathlib
import sqlite3
import subprocess
import sys

import pandas as pd
import yaml

SKILL = pathlib.Path(r"C:\Users\guoyu\.dsh\skills\data-viz")
SCRIPTS = SKILL / "scripts"
BASE = pathlib.Path(r"D:\Claude cade\data\_datasets")
SRC = BASE / "03_text_dirty" / "chinese_orders_gbk.csv"
CASE = BASE / "09_dashboards" / "chinese_orders"
(CASE / "artifacts").mkdir(parents=True, exist_ok=True)

print("=" * 78)
print("步骤 2/3  按用户选单建看板（v3）")
print("=" * 78)

# ---------- 1. 读数据（编码级联；AI 直读路径的本地等价物） ----------
enc_used = next(e for e in ("utf-8-sig", "utf-8", "gbk", "gb18030")
                if _ok(e) if True) if False else None
enc_used = None
for e in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
    try:
        SRC.read_bytes().decode(e); enc_used = e; break
    except UnicodeDecodeError:
        continue
df = pd.read_csv(SRC, encoding=enc_used, dtype=str).fillna("")
for c in ("销售额", "数量", "利润", "折扣"):
    df[c] = pd.to_numeric(df[c], errors="coerce")
print(f"读入 {len(df):,} 行 x {df.shape[1]} 列  (encoding={enc_used})")

# ---------- 2. 用户选单（SKILL.md v3 §2.3） ----------
plan = {
    "intents": ["构成", "排名", "关键少数", "分布", "组间比较", "相关", "数据质量", "趋势", "明细"],
    "deliverables": ["A", "B", "C", "G"],
    "extras": {"top_n": 12, "corr_method": "spearman", "box_group": "产品类别"},
    "notes": "用户要求：分布类图必须带离群点；相关矩阵用斯皮尔曼（抗非线性）；缺失值按维度对比",
}
(CASE / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"用户选单: 意图 {len(plan['intents'])} 项 / 交付物 {'+'.join(plan['deliverables'])}")

# ---------- 3. 口径卡 ----------
cards = [
    ("销售额合计", "全部 4000 行的 销售额 之和", "无（总量指标）", "全部行，含重复订单号",
     "折扣为空的行按标价计入", "一次性快照"),
    ("订单行数", "原始数据行数", "无", "全部行", "无", "一次性快照"),
    ("客户数", "客户字段去重（排除空串）", "无", "非空客户名", "空串 291 行不计入", "一次性快照"),
    ("亏损订单行数", "利润 < 0 的行数", "全部 4000 行", "利润可解析且 < 0", "利润为空不计入", "一次性快照"),
    ("省份分布", "按省份分组的销售额", "无", "全部行", "无", "一次性快照"),
    ("月度趋势", "按订单日期所在月分组的销售额", "无", "日期可解析的行",
     "⚠ 2024-03-15 有 1243 行疑似压平，趋势在该点不可解释", "一次性快照"),
]
cal = ["# 口径卡 · chinese_orders_gbk", "",
       "> 由 AI 依据探源结果提出，**待业务方确认后生效**（v3 流程：探源 → 口径 → 选单 → 出图）。", ""]
for i, (n, a, b, c_, d_, e_) in enumerate(cards, 1):
    cal += [f"## 口径卡 {i}：{n}", "```yaml", f"指标名: {n}", f"分子: {a}", f"分母: {b}",
            f"只算什么: {c_}", f"不算什么: {d_}", f"更新周期: {e_}", "```", ""]
(CASE / "artifacts" / "口径卡.md").write_text("\n".join(cal), encoding="utf-8")
print(f"口径卡 {len(cards)} 张")

# ---------- 4. SQLite 数仓（列名直接用中文业务名，省掉翻译层） ----------
db = CASE / "warehouse.db"
if db.exists():
    db.unlink()
conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute('CREATE TABLE ads_overview ("指标" TEXT, "值" REAL, "单位" TEXT)')
cur.executemany('INSERT INTO ads_overview VALUES (?,?,?)', [
    ("销售额合计", float(df["销售额"].sum()), "元"),
    ("订单行数", float(len(df)), "行"),
    ("客户数", float(df["客户"].replace("", pd.NA).nunique()), "人"),
    ("亏损订单行数", float((df["利润"] < 0).sum()), "行"),
])

# 时间序列表（line 用；全局 time 指向这里）
d2 = df.copy()
dt = pd.to_datetime(d2["订单日期"], errors="coerce", format="mixed")
d2["月份"] = dt.dt.strftime("%Y-%m")
tr = d2.dropna(subset=["月份"]).groupby("月份").agg(销售额=("销售额", "sum"), 行数=("销售额", "size")).reset_index()
tr = tr.sort_values("月份").tail(24)
cur.execute('CREATE TABLE ads_trend ("月份" TEXT, "销售额" REAL, "行数" INTEGER)')
cur.executemany('INSERT INTO ads_trend VALUES (?,?,?)',
                [(r["月份"], float(r["销售额"]), int(r["行数"])) for _, r in tr.iterrows()])
print(f"时间序列: {len(tr)} 个月（{tr['月份'].min()} ~ {tr['月份'].max()}）")

for tbl, col, top in (("ads_category", "产品类别", 20), ("ads_customer_type", "客户类型", 20),
                      ("ads_province", "省份", 20), ("ads_city", "城市", 10)):
    g = df.groupby(col, dropna=False).agg(销售额=("销售额", "sum"), 行数=("销售额", "size")).reset_index()
    g = g.sort_values("销售额", ascending=False).head(top)
    cur.execute(f'CREATE TABLE "{tbl}" ("维度" TEXT, "销售额" REAL, "行数" INTEGER)')
    cur.executemany(f'INSERT INTO "{tbl}" VALUES (?,?,?)',
                    [(str(r[col]) or "(空)", float(r["销售额"]), int(r["行数"])) for _, r in g.iterrows()])

# 折扣档（帕累托 + 构成）
df["折扣档"] = df["折扣"].apply(lambda v: "缺失" if pd.isna(v) else ("无折扣" if v == 0 else f"{v:.1f}"))
g = df.groupby("折扣档").agg(销售额=("销售额", "sum"), 行数=("销售额", "size")).reset_index().sort_values("销售额", ascending=False)
cur.execute('CREATE TABLE ads_discount ("折扣档" TEXT, "销售额" REAL, "行数" INTEGER)')
cur.executemany('INSERT INTO ads_discount VALUES (?,?,?)',
                [(r["折扣档"], float(r["销售额"]), int(r["行数"])) for _, r in g.iterrows()])

# 客户 Top（排名）
g = df[df["客户"] != ""].groupby("客户").agg(销售额=("销售额", "sum"), 行数=("销售额", "size")).reset_index()
g = g.sort_values("销售额", ascending=False).head(12)
cur.execute('CREATE TABLE ads_customer ("客户" TEXT, "销售额" REAL, "行数" INTEGER)')
cur.executemany('INSERT INTO ads_customer VALUES (?,?,?)',
                [(r["客户"], float(r["销售额"]), int(r["行数"])) for _, r in g.iterrows()])

# 统计明细表（box / qq / corr / regress / missing / 直方图 的数据源）
cur.execute('DROP TABLE IF EXISTS dwd_orders')
cur.execute('CREATE TABLE dwd_orders ("订单号" TEXT, "订单日期" TEXT, "客户" TEXT, "客户类型" TEXT, '
            '"城市" TEXT, "省份" TEXT, "产品类别" TEXT, "产品名称" TEXT, "销售额" REAL, "数量" REAL, '
            '"折扣" REAL, "利润" REAL, "折扣档" TEXT)')
cur.executemany('INSERT INTO dwd_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                [tuple(None if (isinstance(v, float) and pd.isna(v)) else v for v in row)
                 for row in df[["订单号", "订单日期", "客户", "客户类型", "城市", "省份", "产品类别",
                                "产品名称", "销售额", "数量", "折扣", "利润", "折扣档"]]
                 .itertuples(index=False, name=None)])
conn.commit()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
conn.close()
print(f"数仓: {len(tables)} 张表 -> {tables}")

# ---------- 5. 声明式配置（含 6 种新统计图） ----------
cfg = {
    "version": 2,
    "title": "订单数据质量与统计分析看板 · 中文 GBK 订单表",
    "time": {"table": "ads_trend", "column": "月份"},
    "metrics": [
        {"id": "sales", "name": "销售额合计", "direction": "up", "unit": "元", "caliber": "销售额合计",
         "source": {"table": "ads_overview", "column": "值", "key": {"指标": "销售额合计"}}},
        {"id": "rows", "name": "订单行数", "direction": "up", "unit": "行", "caliber": "订单行数",
         "source": {"table": "ads_overview", "column": "值", "key": {"指标": "订单行数"}}},
        {"id": "cust", "name": "客户数", "direction": "up", "unit": "人", "caliber": "客户数",
         "source": {"table": "ads_overview", "column": "值", "key": {"指标": "客户数"}}},
        {"id": "loss", "name": "亏损订单行数", "direction": "down", "unit": "行", "caliber": "亏损订单行数",
         "source": {"table": "ads_overview", "column": "值", "key": {"指标": "亏损订单行数"}}},
        {"id": "msales", "name": "月度销售额", "direction": "up", "unit": "元", "caliber": "月度趋势",
         "source": {"table": "ads_trend", "column": "销售额"}},
    ],
    "components": [
        {"id": "k1", "type": "kpi", "metric": "sales"},
        {"id": "k2", "type": "kpi", "metric": "rows"},
        {"id": "k3", "type": "kpi", "metric": "cust"},
        {"id": "k4", "type": "kpi", "metric": "loss"},
        {"id": "h1", "type": "heading", "content": "一、趋势与构成"},
        {"id": "l1", "type": "line", "metrics": ["msales"],
         "label": "月度销售额趋势（⚠ 2024-03 存在日期压平，该点不可解释）"},
        {"id": "p1", "type": "pie", "metric": "sales", "table": "ads_category", "dimension": "维度",
         "label": "产品类别销售额构成", "order": "销售额 DESC"},
        {"id": "p2", "type": "pie", "metric": "sales", "table": "ads_customer_type", "dimension": "维度",
         "label": "客户类型销售额构成", "order": "销售额 DESC"},
        {"id": "h2", "type": "heading", "content": "二、排名与关键少数（帕累托 80/20）"},
        {"id": "pa1", "type": "pareto", "metric": "sales", "table": "ads_province", "dimension": "维度",
         "label": "省份销售额帕累托（找关键少数）", "order": "销售额 DESC", "top": 8},
        {"id": "pa2", "type": "pareto", "metric": "sales", "value_col": "销售额", "table": "ads_discount",
         "dimension": "折扣档", "label": "折扣档位销售额帕累托", "order": "销售额 DESC", "top": 8},
        {"id": "t1", "type": "table", "table": "ads_customer", "columns": ["客户", "销售额", "行数"],
         "top": 12, "title": "客户销售额 Top12"},
        {"id": "h3", "type": "heading", "content": "三、统计分析与分布诊断"},
        {"id": "box1", "type": "box", "table": "dwd_orders", "dimension": "产品类别", "column": "销售额",
         "label": "销售额分布 · 按产品类别（箱线图，含离群点）", "top": 8},
        {"id": "qq1", "type": "qq", "table": "dwd_orders", "column": "利润",
         "label": "利润是否近似正态 · Q-Q 图", "top": 1500},
        {"id": "corr1", "type": "corr", "table": "dwd_orders",
         "columns": ["销售额", "数量", "折扣", "利润"], "method": "spearman"},
        {"id": "reg1", "type": "regress", "table": "dwd_orders", "x": "销售额", "y": "利润",
         "label": "利润 ~ 销售额 回归", "top": 1500},
        {"id": "hist1", "type": "histogram", "table": "dwd_orders", "column": "销售额",
         "label": "销售额分布直方图", "bins": 24},
        {"id": "h4", "type": "heading", "content": "四、数据质量画像"},
        {"id": "miss1", "type": "missing", "table": "dwd_orders", "dimension": "产品类别",
         "label": "缺失值画像（整体 Top 字段 + 分组对比）", "col_top": 12},
        {"id": "tx1", "type": "text", "content":
            "数据说明：源文件 chinese_orders_gbk.csv（GBK 编码，4000 行 × 12 列）。"
            "本看板按 SKILL.md v3 流程产出：AI 直读探源（编码级联→GBK、空串=缺失、订单号重复 2075 行、"
            "1243 行日期被压平、折扣列 1047 行字面 None）→ 口径卡 → 用户选单 → 声明式配置 → 渲染 → 闸门。"
            "统计图由引擎本地计算：箱线图用线性插值四分位 + 1.5×IQR 离群点；Q-Q 用 Acklam 正态分位数；"
            "相关矩阵为斯皮尔曼秩相关；回归给出斜率/截距/R²。转发：单文件离线网页，双击即看。"},
    ],
    "drill": {
        "l2": {"dimensions": [
            {"table": "ads_category", "dimension": "维度", "label": "按产品类别", "order": "销售额 DESC"},
            {"table": "ads_customer_type", "dimension": "维度", "label": "按客户类型", "order": "销售额 DESC"},
            {"table": "ads_province", "dimension": "维度", "label": "按省份", "order": "销售额 DESC"},
            {"table": "ads_city", "dimension": "维度", "label": "按城市", "order": "销售额 DESC"},
        ]},
        "l3": {"table": "dwd_orders",
               "columns": ["订单号", "订单日期", "客户", "城市", "产品类别", "销售额", "利润"],
               "dimension_map": {}, "limit": 200},
    },
}
(CASE / "dashboard.config.yaml").write_text(
    yaml.dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False), encoding="utf-8")
print(f"配置: {len(cfg['components'])} 个组件（含 box/qq/pareto×2/corr/regress 六种新统计图）")

# ---------- 6. 补中文业务名（幂等） ----------
GEN = SCRIPTS / "render_universal_dashboard.py"
src = GEN.read_text(encoding="utf-8")
MARK = "# ---- 演示数据集字典 v3 ----"
if MARK not in src:
    add = (f"    {MARK}\n"
           '    "值": "数值", "单位": "单位", "指标": "指标", "维度": "维度",\n'
           '    "销售额合计": "销售额合计", "订单行数": "订单行数", "客户数": "客户数",\n'
           '    "亏损订单行数": "亏损订单行数", "月度销售额": "月度销售额", "月份": "月份",\n'
           '    "城市": "城市", "省份": "省份", "产品类别": "产品类别", "客户类型": "客户类型",\n'
           '    "产品名称": "产品名称", "客户": "客户", "订单号": "订单号", "订单日期": "订单日期",\n'
           '    "折扣": "折扣", "折扣档": "折扣档位", "销售额": "销售额", "数量": "数量", "利润": "利润",\n'
           '    "行数": "行数", "总数": "总数", "累计占比": "累计占比",\n')
    i = src.find("FIELD_CN = {\n")
    assert i > 0
    src = src[:i + len("FIELD_CN = {\n")] + add + src[i + len("FIELD_CN = {\n"):]
    GEN.write_text(src, encoding="utf-8")
    print("渲染引擎: 已补录中文业务名")
else:
    print("渲染引擎: 中文业务名已存在")

# ---------- 7. 渲染 + 闸门 ----------
r = subprocess.run([sys.executable, "-X", "utf8", str(GEN), str(CASE)],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
print("\n--- 渲染引擎 ---")
print((r.stdout or "").strip()[-900:])
if r.returncode != 0:
    print("渲染失败 STDERR:\n", (r.stderr or "").strip()[-1500:])
    sys.exit(1)

html = CASE / "dashboard.html"
chk = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "dashboard_check.py"), str(html)],
                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
print("\n--- 质量闸门 dashboard_check ---")
print((chk.stdout or "").strip()[-1000:])
print(f"\n[产物] {html}  {html.stat().st_size/1024/1024:.2f} MB")
