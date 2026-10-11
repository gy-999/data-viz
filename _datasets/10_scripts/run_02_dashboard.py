"""data-viz 正式测试 · 第 2 步：干看板（按 data-viz 的方式：口径卡 → SQLite 数仓 → 声明式 config → 渲染 → 闸门）

数据: 03_text_dirty/chinese_orders_gbk.csv (GBK, 4000 行, 中文表头)
口径: 见 artifacts/口径卡.md —— 由 AI 依据探源结果提出，供业务方确认
"""
import json
import pathlib
import re
import sqlite3
import subprocess
import sys

import pandas as pd

SKILL = pathlib.Path(r"C:\Users\guoyu\.dsh\skills\data-viz")
SCRIPTS = SKILL / "scripts"
CASE = pathlib.Path(__file__).resolve().parent.parent / "09_dashboards" / "chinese_orders"
SRC = pathlib.Path(r"D:\Claude cade\data\_datasets\03_text_dirty\chinese_orders_gbk.csv")
CASE.mkdir(parents=True, exist_ok=True)
(CASE / "artifacts").mkdir(exist_ok=True)

print("=" * 78)
print("步骤 2/3  建干看板")
print("=" * 78)

# ---------- 1. 读数据（编码级联） ----------
enc_used = None
for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
    try:
        SRC.read_bytes().decode(enc)
        enc_used = enc
        break
    except UnicodeDecodeError:
        continue
df = pd.read_csv(SRC, encoding=enc_used, dtype=str).fillna("")
print(f"读入: {len(df):,} 行 x {df.shape[1]} 列  (encoding={enc_used})")

for c in ("销售额", "数量", "利润", "折扣"):
    df[c] = pd.to_numeric(df[c], errors="coerce")
# 折扣里的字面 None 已被 to_numeric 转成 NaN
n_discount_na = int(df["折扣"].isna().sum())

# ---------- 2. 口径卡（AI 依据探源结果提出，待业务确认） ----------
cards = [
    ("销售额合计", "全部 4000 行的 销售额 之和", "无（总量指标）",
     "全部行，含重复订单号", "无（折扣为空的行也计入，按标价计）", "一次性快照"),
    ("订单数与订单行数", "订单数 = 订单号去重计数；订单行数 = 原始行数", "订单行数 4000 / 订单数 1925",
     "两个口径并列展示", "不把重复订单号当两笔订单", "一次性快照"),
    ("客户数", "客户 字段去重计数（排除空串）", "无", "非空客户名", "空串 291 行不计入", "一次性快照"),
    ("亏损订单行占比", "利润 < 0 的行数 / 全部行数", "全部 4000 行",
     "利润可解析且小于 0 的行", "利润为空的行不计入分子", "一次性快照"),
    ("省份分布", "按 省份 分组的销售额与行数", "无", "全部行", "无", "一次性快照"),
    ("月度趋势", "按 订单日期 所在月分组的销售额", "无", "日期可解析的行",
     "⚠ 2024-03-15 有 1243 行疑似被压平，趋势图在此点不可解释", "一次性快照"),
]
cal = ["# 口径卡 · chinese_orders_gbk", "",
       "> 由 data-viz 依据探源结果提出（AI 出内容），**待业务方确认后生效**。", ""]
for i, (name, num_, den, inc, exc, upd) in enumerate(cards, 1):
    cal += [f"## 口径卡 {i}：{name}", "```yaml", f"指标名: {name}", f"分子: {num_}",
            f"分母: {den}", f"只算什么: {inc}", f"不算什么: {exc}", f"更新周期: {upd}", "```", ""]
(CASE / "artifacts" / "口径卡.md").write_text("\n".join(cal), encoding="utf-8")
print(f"口径卡: {len(cards)} 张 -> artifacts/口径卡.md")

# ---------- 3. 聚合进 SQLite 数仓 ----------
db = CASE / "warehouse.db"
if db.exists():
    db.unlink()
conn = sqlite3.connect(db)
cur = conn.cursor()

total_sales = float(df["销售额"].sum())
order_rows = len(df)
orders = df["订单号"].nunique()
customers = df["客户"].replace("", pd.NA).nunique()
loss_rows = int((df["利润"] < 0).sum())

cur.execute("CREATE TABLE ads_overview (total_sales REAL, order_rows INTEGER, orders INTEGER, "
            "customers INTEGER, loss_rows INTEGER, profit_sum REAL, discount_na INTEGER)")
cur.execute("INSERT INTO ads_overview VALUES (?,?,?,?,?,?,?)",
            (total_sales, order_rows, orders, customers, loss_rows, float(df["利润"].sum()), n_discount_na))

def make_ads(table, col, metric="销售额", top=20, agg="sum", filename=None):
    cur.execute(f"DROP TABLE IF EXISTS {table}")
    if agg == "sum":
        g = df.groupby(col, dropna=False).agg(sales=(metric, "sum"), cnt=(metric, "size")).reset_index()
        g = g.sort_values("sales", ascending=False)
        cur.execute(f"CREATE TABLE {table} (dim TEXT, sales REAL, cnt INTEGER)")
        cur.executemany(f"INSERT INTO {table} VALUES (?,?,?)",
                        [(str(r[col]) or "(空)", float(r["sales"]), int(r["cnt"])) for _, r in g.head(top).iterrows()])
    else:
        g = df[col].astype(str).value_counts().head(top)
        cur.execute(f"CREATE TABLE {table} (dim TEXT, cnt INTEGER)")
        cur.executemany(f"INSERT INTO {table} VALUES (?,?)", [(k, int(v)) for k, v in g.items()])
    return table

make_ads("ads_category", "产品类别")
make_ads("ads_customer_type", "客户类型")
make_ads("ads_province", "省份")
make_ads("ads_city", "城市", top=10)

# 客户 Top
g = df[df["客户"] != ""].groupby("客户").agg(sales=("销售额", "sum"), cnt=("销售额", "size")).reset_index()
g = g.sort_values("sales", ascending=False).head(12)
cur.execute("CREATE TABLE ads_customer (customer TEXT, sales REAL, cnt INTEGER)")
cur.executemany("INSERT INTO ads_customer VALUES (?,?,?)",
                [(r["客户"], float(r["sales"]), int(r["cnt"])) for _, r in g.iterrows()])

# 折扣分档
df["折扣档"] = df["折扣"].apply(lambda v: "缺失" if pd.isna(v) else ("无折扣" if v == 0 else f"{v:.1f}"))
g = df.groupby("折扣档").agg(sales=("销售额", "sum"), cnt=("销售额", "size")).reset_index()
g = g.sort_values("sales", ascending=False)
cur.execute("CREATE TABLE ads_discount (dim TEXT, sales REAL, cnt INTEGER)")
cur.executemany("INSERT INTO ads_discount VALUES (?,?,?)",
                [(r["折扣档"], float(r["sales"]), int(r["cnt"])) for _, r in g.iterrows()])

# 月度趋势
d2 = df.copy()
dt = pd.to_datetime(d2["订单日期"], errors="coerce", format="mixed", dayfirst=False)
d2["ym"] = dt.dt.strftime("%Y-%m")
trend = d2.dropna(subset=["ym"]).groupby("ym").agg(sales=("销售额", "sum"), cnt=("销售额", "size")).reset_index()
trend = trend.sort_values("ym").tail(24)
cur.execute("CREATE TABLE ads_month (ym TEXT, sales REAL, cnt INTEGER)")
cur.executemany("INSERT INTO ads_month VALUES (?,?,?)", [(r["ym"], float(r["sales"]), int(r["cnt"])) for _, r in trend.iterrows()])

# 码值字典 + 数据质量说明
cur.execute("CREATE TABLE ads_codebook (fld TEXT, val TEXT, meaning TEXT, basis TEXT)")
cb = [
    ("客户类型", "个人/企业/家庭办公", "业务分类（原样保留）", "源数据"),
    ("客户类型", "(空)", "168 行缺失，未归类", "实测"),
    ("产品类别", "办公用品/家具/技术", "业务分类（原样保留）", "源数据"),
    ("订单号", "重复 2075 行", "同一订单号对应多个商品行；计订单数须去重", "实测"),
    ("订单日期", "2024-03-15", "1243 行落在同一天，疑似被压平，时间趋势不可解释", "实测·待确认"),
    ("订单日期", "10/30/2018 等", "另一套 M/D/YYYY 格式，与 2024-xx-xx 并存", "实测·待确认"),
    ("折扣", "None", "1047 行字面 None，实为缺失值", "实测"),
    ("利润", "负值 716 行", "亏损订单行", "实测"),
]
cur.executemany("INSERT INTO ads_codebook VALUES (?,?,?,?)", cb)

cur.execute("DROP TABLE IF EXISTS dwd_orders")
cur.execute('CREATE TABLE dwd_orders ("订单号" TEXT, "订单日期" TEXT, "客户" TEXT, "客户类型" TEXT, '
            '"城市" TEXT, "省份" TEXT, "产品类别" TEXT, "产品名称" TEXT, "销售额" REAL, "数量" REAL, '
            '"折扣" REAL, "利润" REAL)')
dwd = df.head(30000)[["订单号", "订单日期", "客户", "客户类型", "城市", "省份", "产品类别",
                      "产品名称", "销售额", "数量", "折扣", "利润"]]
cur.executemany('INSERT INTO dwd_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                [tuple(None if (isinstance(v, float) and pd.isna(v)) else v for v in row)
                 for row in dwd.itertuples(index=False, name=None)])
conn.commit()
conn.close()
print(f"数仓: warehouse.db  表={[r[0] for r in sqlite3.connect(db).execute(chr(83)+'ELECT name FROM sqlite_master WHERE type=' + chr(39)+'table'+chr(39))]}")

# ---------- 4. 声明式看板配置 ----------
cfg = {
    "version": 2,
    "title": "订单数据质量与分析看板 · 中文 GBK 订单表",
    "metrics": [
        {"id": "sales", "name": "销售额合计", "direction": "up", "unit": "元", "caliber": "销售额合计",
         "source": {"table": "ads_overview", "column": "total_sales"}},
        {"id": "order_rows", "name": "订单行数", "direction": "up", "unit": "行", "caliber": "订单数与订单行数",
         "source": {"table": "ads_overview", "column": "order_rows"}},
        {"id": "customers", "name": "客户数", "direction": "up", "unit": "人", "caliber": "客户数",
         "source": {"table": "ads_overview", "column": "customers"}},
        {"id": "loss", "name": "亏损订单行占比", "direction": "down", "unit": "%", "caliber": "亏损订单行占比",
         "source": {"table": "ads_overview", "column": "loss_rows"}},
    ],
    "components": [
        {"id": "h1", "type": "heading", "content": "一、核心指标（鼠标悬停 KPI 卡可看口径分子/分母）"},
        {"id": "k1", "type": "kpi", "metric": "sales"},
        {"id": "k2", "type": "kpi", "metric": "order_rows"},
        {"id": "k3", "type": "kpi", "metric": "customers"},
        {"id": "k4", "type": "kpi", "metric": "loss"},
        {"id": "h2", "type": "heading", "content": "二、构成分析"},
        {"id": "c1", "type": "pie", "metric": "sales", "table": "ads_category", "dimension": "dim",
         "label": "产品类别销售额构成", "order": "sales DESC"},
        {"id": "c2", "type": "pie", "metric": "sales", "table": "ads_customer_type", "dimension": "dim",
         "label": "客户类型销售额构成", "order": "sales DESC"},
        {"id": "c3", "type": "bar", "metric": "sales", "table": "ads_province", "dimension": "dim",
         "label": "省份销售额分布", "order": "sales DESC"},
        {"id": "c4", "type": "bar", "metric": "sales", "table": "ads_discount", "dimension": "dim",
         "label": "折扣档位销售额", "order": "sales DESC"},
        {"id": "h3", "type": "heading", "content": "三、趋势与明细"},
        {"id": "c5", "type": "line", "metric": "sales", "table": "ads_month", "dimension": "ym",
         "label": "月度销售额趋势（⚠ 2024-03 存在日期压平，该点不可解释）", "order": "ym ASC"},
        {"id": "c6", "type": "table", "table": "ads_customer", "columns": ["customer", "sales", "cnt"],
         "top": 12, "title": "客户销售额 Top12"},
        {"id": "h4", "type": "heading", "content": "四、码值字典与数据质量（转发前请先读这里）"},
        {"id": "c7", "type": "table", "table": "ads_codebook", "columns": ["fld", "val", "meaning", "basis"],
         "top": 12, "title": "码值字典 / 数据质量说明"},
        {"id": "t1", "type": "text", "content":
            "数据说明：源文件 chinese_orders_gbk.csv（GBK 编码，4000 行 × 12 列，中文表头）。"
            "本看板为 data-viz 实测样例：先探源（编码级联→GBK、空串=缺失、订单号重复 2075 行、"
            "日期被压平 1243 行），再按口径卡聚合。订单数按订单号去重（1925），订单行数为 4000。"
            "折扣列 1047 行为字面 None（视为缺失）。转发：单文件离线网页，双击即看，无需联网。"},
    ],
    "drill": {
        "l2": {"dimensions": [
            {"table": "ads_category", "dimension": "dim", "label": "按产品类别", "order": "sales DESC"},
            {"table": "ads_customer_type", "dimension": "dim", "label": "按客户类型", "order": "sales DESC"},
            {"table": "ads_province", "dimension": "dim", "label": "按省份", "order": "sales DESC"},
            {"table": "ads_city", "dimension": "dim", "label": "按城市", "order": "sales DESC"},
        ]},
        "l3": {"table": "dwd_orders",
               "columns": ["订单号", "订单日期", "客户", "城市", "产品类别", "销售额", "利润"],
               "dimension_map": {},
               "limit": 200},
    },
}
import yaml
(CASE / "dashboard.config.yaml").write_text(
    yaml.dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False), encoding="utf-8")
print("配置: dashboard.config.yaml")

# ---------- 5. 补中文业务名到渲染引擎（幂等） ----------
GEN = SCRIPTS / "render_universal_dashboard.py"
src = GEN.read_text(encoding="utf-8")
MARK = "# ---- 中文订单表补充字典 ----"
if MARK not in src:
    add = (f"    {MARK}\n"
           '    "dim": "维度", "sales": "销售额", "cnt": "行数", "customer": "客户", "ym": "月份",\n'
           '    "总销售额": "销售额合计", "订单行数": "订单行数", "客户数": "客户数",\n'
           '    "亏损占比": "亏损订单行占比", "产品类别": "产品类别", "客户类型": "客户类型",\n'
           '    "省份": "省份", "城市": "城市", "折扣档": "折扣档位", "折扣": "折扣",\n'
           '    "订单号": "订单号", "订单日期": "订单日期", "客户": "客户", "销售额": "销售额",\n'
           '    "数量": "数量", "利润": "利润", "产品名称": "产品名称",\n')
    anchor = "FIELD_CN = {\n"
    i = src.find(anchor)
    assert i > 0, "未找到 FIELD_CN"
    src = src[:i + len(anchor)] + add + src[i + len(anchor):]
    GEN.write_text(src, encoding="utf-8")
    print("渲染引擎: 已补录中文业务名（幂等标记）")
else:
    print("渲染引擎: 中文业务名已存在，跳过")

# ---------- 6. 渲染 + 闸门 ----------
r = subprocess.run([sys.executable, "-X", "utf8", str(GEN), str(CASE)],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
print("\n--- 渲染引擎 ---")
print((r.stdout or "").strip()[-500:])
if r.returncode != 0:
    print("STDERR:", (r.stderr or "").strip()[-1200:])
    sys.exit(1)

html = CASE / "dashboard.html"
chk = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "dashboard_check.py"), str(html)],
                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("\n--- 质量闸门 dashboard_check ---")
print((chk.stdout or "").strip()[-800:])
print(f"\n[产物] {html}  {html.stat().st_size/1024/1024:.2f} MB")
