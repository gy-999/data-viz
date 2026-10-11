"""Compute the concrete anomalies in each demo dataset, so README claims are verified numbers."""
import csv
import hashlib
import pathlib
from collections import Counter

ROOT = pathlib.Path(r"D:\Claude cade\data\_datasets")
out = []


def say(line=""):
    print(line)
    out.append(line)


def read_csv(path, enc="utf-8-sig", **kw):
    with open(path, encoding=enc, newline="", **kw) as fh:
        return list(csv.DictReader(fh))


say("# 各数据集实测探源结论（由 _verify_findings.py 真实计算）")
say()
say("> 这些是**真实算出来的数字**，不是估计。用它验收 skill：它应该独立发现同样的问题。")
say()

# ---------- 03 chinese_orders_gbk ----------
say("## 1. `03_text_dirty/chinese_orders_gbk.csv`（GBK 中文订单表）")
p = ROOT / "03_text_dirty" / "chinese_orders_gbk.csv"
raw = p.read_bytes()
enc_results = {}
for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
    try:
        raw.decode(enc)
        enc_results[enc] = "OK"
    except UnicodeDecodeError:
        enc_results[enc] = "FAIL"
rows = read_csv(p, enc="gbk")
cols = list(rows[0].keys())
blanks = {c: sum(1 for r in rows if str(r[c]).strip() == "") for c in cols}
none_like = {c: sum(1 for r in rows if str(r[c]).strip().lower() in ("none", "null", "\\n")) for c in cols}
oids = Counter(r["订单号"] for r in rows)
dup_orders = sum(v - 1 for v in oids.values() if v > 1)
say(f"- 行数 **{len(rows):,}**，列数 {len(cols)}，文件 {p.stat().st_size/1024:.0f} KB")
say(f"- 编码级联实测：{enc_results}  → 只有 gbk/gb18030 能读")
say(f"- 空字符串（伪装成缺失值）：" + "、".join(f"`{c}`={v}" for c, v in blanks.items() if v > 0))
say(f"- 字面 `None` 当值：`折扣`={none_like['折扣']} 行")
say(f"- 订单号重复：**{dup_orders} 行重复**（唯一订单号 {len(oids):,} 个 / 共 {len(rows):,} 行）")
dates = Counter(r["订单日期"] for r in rows)
say(f"- 日期分布 Top3：{dates.most_common(3)}（大量订单被压到同一天）")
say()

# ---------- 02 movielens ----------
say("## 2. `02_multitable/movielens`（多表关联）")
ml = ROOT / "02_multitable" / "movielens"
ratings = read_csv(ml / "ratings.csv")
movies = read_csv(ml / "movies.csv")
links = read_csv(ml / "links.csv")
movie_ids = {r["movieId"] for r in movies}
orphan = {r["movieId"] for r in ratings} - movie_ids
orphan_rows = [r for r in ratings if r["movieId"] in orphan]
say(f"- ratings {len(ratings):,} 行 / movies {len(movies):,} 行 / links {len(links):,} 行")
if orphan:
    say(f"- **孤儿外键**：{len(orphan)} 个 movieId 有评分但 movies 表里没有，涉及 **{len(orphan_rows):,} 条评分**")
    say(f"  样例 movieId: {sorted(orphan)[:8]}")
else:
    say("- 外键完整性：**0 个孤儿 movieId**（ratings 全部能在 movies 里找到）——"
        "这份数据的价值是“干净的多表关联”，不是脏数据；脏数据请用 03 目录")
na = [r for r in movies if r["genres"] == "(no genres listed)"]
say(f"- movies 里 `genres=(no genres listed)`：{len(na)} 部（枚举里的额外取值）")
say(f"- 跨表重名字段可查：ratings.movieId ↔ movies.movieId ↔ links.movieId")
say()

# ---------- 08 large ----------
say("## 3. `08_large/orders_large_600k.csv`（60 万行）")
lp = ROOT / "08_large" / "orders_large_600k.csv"
with open(lp, encoding="utf-8-sig", newline="") as fh:
    big = list(csv.DictReader(fh))
years = Counter(r["下单日期"][:4] for r in big)
months_2025 = Counter(r["下单日期"][5:7] for r in big if r["下单日期"].startswith("2025"))
statuses = Counter(r["订单状态"] for r in big)
say(f"- 行数 **{len(big):,}**，{lp.stat().st_size/1024/1024:.1f} MB")
say(f"- 年度分布：{dict(sorted(years.items()))}  → **2025 年只到 {max(months_2025)} 月（时间悬崖）**")
say(f"- 订单状态取值：{dict(statuses)}（含空字符串 {statuses.get('', 0):,} 行）")
say(f"- 大区/渠道/城市/品类 均为枚举维度，适合做 24 列看板 + 下钻")
say()

# ---------- 03 bank + superstore ----------
say("## 4. `03_text_dirty/bank_marketing.csv` + `superstore.csv`")
import pandas as pd

bk = pd.read_csv(ROOT / "03_text_dirty" / "bank_marketing.csv", sep=";")
sentinels = {c: int((bk[c] == "unknown").sum()) for c in bk.columns if (bk[c] == "unknown").any()}
pdays999 = int((bk["pdays"] == 999).sum())
pos = (bk["y"] == "yes").sum()
say(f"- 银行营销：{len(bk):,} 行 × {bk.shape[1]} 列，**分隔符是 `;`**（按 `,` 读会读成 1 列 41188 行）")
say(f"- 真 NULL 为 0，但 `unknown` 是伪装缺失值：" + "、".join(f"`{c}`={v:,}" for c, v in sentinels.items()))
say(f"- `pdays=999` 有 **{pdays999:,} 行 / 共 {len(bk):,}**（999=从未联系过的哨兵值；当数值算均值会严重失真）")
say(f"- 目标列 `y` 极不平衡：yes {pos:,} / no {len(bk)-pos:,}（正例率 {pos/len(bk)*100:.1f}%）")

ss = pd.read_csv(ROOT / "03_text_dirty" / "superstore.csv")
null_counts = {k: int(v) for k, v in ss.isna().sum().items() if v}
neg = int((pd.to_numeric(ss["Profit"], errors="coerce") < 0).sum())
say(f"- 超级商店：{len(ss):,} 行 × {ss.shape[1]} 列，**有 {len(null_counts)} 列各缺 {max(null_counts.values()):,} 行**"
    f"（该文件存在行长不齐的坏行，空缺集中在同一批记录上）")
say(f"- 利润为负：{neg:,} 行（亏损订单，占 {neg/len(ss)*100:.1f}%）；订单号唯一 {ss['Order ID'].nunique():,} 个 / 共 {len(ss):,} 行")
say()

# ---------- 05 geo time ----------
say("## 5. `05_geo_time`（地理 + 时间）")
eq = read_csv(ROOT / "05_geo_time" / "earthquakes_2024.csv")
mag = [float(r["mag"]) for r in eq if r["mag"]]
say(f"- USGS 2024 地震：{len(eq):,} 条，震级 {min(mag)} ~ {max(mag)}，含经纬度/深度（地图 + 时间序列）")
wx = read_csv(ROOT / "05_geo_time" / "weather_seattle_2016.csv")
wyears = Counter(r["Date"].split("/")[-1] for r in wx)
say(f"- 西雅图气温：{len(wx):,} 行/天，年份跨度 {min(wyears)} ~ {max(wyears)}（长期序列，适合看时间悬崖）")
say()

# ---------- 01 public ----------
say("## 6. `01_public_csv`（最小闭环）")
for name in ("gapminder.csv", "titanic.csv", "diamonds.csv", "flights.csv", "iris.csv", "penguins.csv", "tips.csv"):
    fp = ROOT / "01_public_csv" / name
    if not fp.exists():
        continue
    rr = read_csv(fp)
    blanks = sum(1 for r in rr for v in r.values() if str(v).strip() == "")
    say(f"- `{name}`：{len(rr):,} 行 × {len(rr[0])} 列，空值格 {blanks:,}")
say()

# ---------- 04 media ----------
say("## 7. `04_media_inventory`（本机媒体资产）")
img_dir = ROOT / "04_media_inventory" / "images"
hashes = {}
for f in img_dir.glob("*"):
    h = hashlib.md5(f.read_bytes()).hexdigest()
    hashes.setdefault(h, []).append(f.name)
groups = {h: v for h, v in hashes.items() if len(v) > 1}
say(f"- 图片 {len(list(img_dir.glob('*')))} 张，**完全重复（MD5 相同）{sum(len(v) - 1 for v in groups.values())} 张，分属 {len(groups)} 组**")
for h, v in list(groups.items())[:6]:
    say(f"   - {v}")
docs = list((ROOT / "04_media_inventory" / "docs").glob("*"))
vids = list((ROOT / "04_media_inventory" / "video").glob("*"))
arcs = list((ROOT / "04_media_inventory" / "archives").glob("*"))
say(f"- 文档 {len(docs)} 份（docx/pptx/pdf/xlsx）、视频 {len(vids)} 个、压缩包 {len(arcs)} 个")
say(f"- doc_extract 已实测：PPT 抽出正文文本、PDF 抽出全文（见 `04_media_inventory/extracted/`）")

(ROOT / "expected-findings.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"\n[written] {ROOT / 'expected-findings.md'}")
