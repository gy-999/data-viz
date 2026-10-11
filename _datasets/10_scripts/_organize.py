"""Organize downloaded demo data into the skill's analysis angles.

Creates: classified folders, a manifest.csv, a README with how-to-use, and a few
purpose-made demo files (GBK-encoded Chinese CSV, SQL script, >500k-row file).
Re-runnable: existing targets are overwritten.
"""
import json
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path(r"D:\Claude cade\data\_datasets")
RAW = ROOT / "_raw"
GROUPS = {
    "01_public_csv": "小体量 CSV，练最小闭环：探源 → 口径 → 看板 → 总结报告",
    "02_multitable": "多表关联：孤儿外键、跨表重名字段、多源合并",
    "03_text_dirty": "有脏数据的真实业务表：空串当空值、枚举越界、重复行、口径歧义",
    "04_media_inventory": "本机媒体与文档资产：图片/视频/文档/压缩包（media_probe、doc_extract）",
    "05_geo_time": "地理 + 时间：地图分布、时间悬崖、坐标缺失",
    "06_excel": "Excel 通路：多 sheet、原生图表交付",
    "07_sql": "SQL 脚本通路：从建表+INSERT 里提取数据",
    "08_large": "大数据量通路：>50 万行时的分块/抽样自适应",
}

for d in GROUPS:
    (ROOT / d).mkdir(parents=True, exist_ok=True)


def put(src: pathlib.Path, group: str, dst_name: str = None, note: str = "") -> dict:
    dst = ROOT / group / (dst_name or src.name)
    if src.exists():
        shutil.copy2(src, dst)
        return {"group": group, "file": dst.name, "bytes": dst.stat().st_size,
                "source_file": src.name, "note": note}
    return {"group": group, "file": dst.name, "bytes": 0, "source_file": src.name,
            "note": "MISSING: " + note}


manifest = []

# ---------- 01 public csv ----------
for name, note in [
    ("tips.csv", "餐厅小费：分类维度+数值指标，最小演示样本"),
    ("flights.csv", "月度航班旅客数：时间序列 / 时间悬崖练手"),
    ("iris.csv", "鸢尾花：三分类枚举，最经典的分类演示"),
    ("penguins.csv", "企鹅：含缺失值的分类演示"),
    ("gapminder.csv", "国家-年-寿命-GDP：多国多年度，适合折线+散点看板"),
    ("titanic.csv", "泰坦尼克：Age/Cabin 大量缺失，生还率口径歧义经典案例"),
    ("diamonds.csv", "53940 行钻石：价格/克拉/切工多维分析"),
]:
    manifest.append(put(RAW / name, "01_public_csv", note=note))

# ---------- 02 multitable (MovieLens) ----------
ml_zip = RAW / "ml-latest-small.zip"
ml_dir = ROOT / "02_multitable" / "movielens"
if ml_zip.exists():
    with zipfile.ZipFile(ml_zip) as z:
        for member in z.namelist():
            if member.endswith("/"):
                continue
            target = ml_dir / pathlib.Path(member).name
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as fsrc, open(target, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
            manifest.append({"group": "02_multitable/movielens", "file": target.name,
                             "bytes": target.stat().st_size, "source_file": "ml-latest-small.zip",
                             "note": "多表关联：ratings/movies/links/tags，可查孤儿 movieId"})

# ---------- 03 text/dirty ----------
manifest.append(put(RAW / "bank_marketing.csv", "03_text_dirty",
                    note="分号分隔+带引号；枚举越界、pdays=999 缺省值陷阱、unknown 满天飞"))
manifest.append(put(RAW / "superstore.csv", "03_text_dirty",
                    note="真实订单表：重复订单号、日期格式不一致、折扣列有 None 字符串"))

# 中文 + GBK 编码的演示表（由 superstore 本地化改写，用于验证编码级联与中文可读性）
src = RAW / "superstore.csv"
gbk_path = ROOT / "03_text_dirty" / "chinese_orders_gbk.csv"
if src.exists():
    import csv
    import random
    random.seed(11)
    cities = [("杭州市", "浙江省"), ("宁波市", "浙江省"), ("成都市", "四川省"),
              ("武汉市", "湖北省"), ("西安市", "陕西省"), ("广州市", "广东省")]
    seg_cn = {"Consumer": "个人", "Corporate": "企业", "Home Office": "家庭办公"}
    cat_cn = {"Furniture": "家具", "Office Supplies": "办公用品", "Technology": "技术"}
    with open(src, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    with open(gbk_path, "w", encoding="gbk", newline="", errors="replace") as fh:
        w = csv.writer(fh)
        w.writerow(["订单号", "订单日期", "客户", "客户类型", "城市", "省份",
                    "产品类别", "产品名称", "销售额", "数量", "折扣", "利润"])
        # 故意留坑：空字符串当空值、折扣有 None、订单号重复、末年只到 3 月
        for i, r in enumerate(rows[:4000]):
            city, prov = random.choice(cities)
            seg = seg_cn.get(r.get("Segment", ""), r.get("Segment", ""))
            cat = cat_cn.get(r.get("Category", ""), r.get("Category", ""))
            odate = r.get("Order Date", "")
            if random.random() < 0.3:
                odate = "2024-03-15"
            w.writerow([
                r.get("Order ID", "") if random.random() > 0.05 else rows[i % 37].get("Order ID", ""),
                odate,
                r.get("Customer Name", "") if random.random() > 0.08 else "",
                seg if random.random() > 0.05 else "",
                city,
                prov,
                cat,
                r.get("Product Name", ""),
                r.get("Sales", ""),
                r.get("Quantity", ""),
                r.get("Discount", "") if random.random() > 0.25 else "None",
                r.get("Profit", ""),
            ])
    manifest.append({"group": "03_text_dirty", "file": gbk_path.name,
                     "bytes": gbk_path.stat().st_size, "source_file": "superstore.csv (locally rewritten)",
                     "note": "GBK 编码 + 中文表头：故意含空串空值/重复订单号/None 折扣，验证编码级联与探源六项"})

# ---------- 05 geo/time ----------
manifest.append(put(RAW / "earthquakes_2024.csv", "05_geo_time",
                    note="USGS 真实地震：经纬度、深度、震级、时间，适合地图+时间序列"))
manifest.append(put(RAW / "weather_seattle_2016.csv", "05_geo_time",
                    note="1948 起逐日气温：长期时间序列，适合时间悬崖演示"))
manifest.append(put(RAW / "china_region_codes.csv", "05_geo_time", "china_region_codes.json",
                    note="全国省市区街道四级行政区划 JSON（中文）"))

# ---------- 06 excel ----------
manifest.append(put(RAW / "financial_sample.xlsx", "06_excel",
                    note="微软官方 Financial Sample：701 行 x 16 列，Segment/Country/Product/利润"))

# ---------- 07 sql ----------
manifest.append(put(RAW / "chinook.sql", "07_sql", "chinook_sqlite.sql",
                    note="Chinook 音乐库建表+INSERT 脚本：11 张表，含外键关系"))

# ---------- 08 large (>500k rows) ----------
large = ROOT / "08_large" / "orders_large_600k.csv"
if not large.exists():
    import csv
    import random
    from datetime import date, timedelta
    random.seed(2026)
    regions = ["华东", "华南", "华北", "西南", "西北", "东北"]
    channels = ["线上", "门店", "分销", "直营"]
    status = ["已完成", "已取消", "退款中", "待发货", ""]
    lines = ["订单号,下单日期,大区,渠道,城市,品类,数量,单价,金额,订单状态,客户等级"]
    base = date(2023, 1, 1)
    for i in range(600000):
        d = base + timedelta(days=random.randint(0, 730))
        if d.year == 2025 and d.month > 3:
            d = date(2025, 3, random.randint(1, 28))  # 末年只到 3 月 -> 时间悬崖
        qty = random.randint(1, 20)
        price = round(random.uniform(9.9, 2999), 2)
        lines.append(",".join([
            f"SO{1000000 + i}",
            d.isoformat(),
            random.choice(regions),
            random.choice(channels),
            random.choice(["杭州市", "宁波市", "成都市", "武汉市", "西安市", "广州市", "沈阳市"]),
            random.choice(["家电", "数码", "服饰", "食品", "家居"]),
            str(qty),
            f"{price:.2f}",
            f"{qty * price:.2f}",
            random.choice(status),
            random.choice(["高", "中", "低"]),
        ]))
    large.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
manifest.append({"group": "08_large", "file": large.name, "bytes": large.stat().st_size,
                 "source_file": "(generated)", "note": "60 万行 x 11 列：验证 >50 万行时的分块/抽样自适应与时间悬崖"})

# ---------- 04 media inventory (already built) ----------
inv = ROOT / "04_media_inventory"
img = list((inv / "images").glob("*")) if (inv / "images").exists() else []
vid = list((inv / "video").glob("*")) if (inv / "video").exists() else []
doc = list((inv / "docs").glob("*")) if (inv / "docs").exists() else []
arc = list((inv / "archives").glob("*")) if (inv / "archives").exists() else []
manifest.append({"group": "04_media_inventory", "file": f"{len(img)} images", "bytes": sum(p.stat().st_size for p in img),
                 "source_file": "local machine scan", "note": "含 18 组完全重复图，media_probe 重复检测演示"})
manifest.append({"group": "04_media_inventory", "file": f"{len(vid)} videos", "bytes": sum(p.stat().st_size for p in vid),
                 "source_file": "local machine scan", "note": "视频文件级盘点"})
manifest.append({"group": "04_media_inventory", "file": f"{len(doc)} documents", "bytes": sum(p.stat().st_size for p in doc),
                 "source_file": "local machine scan", "note": "docx/pptx/pdf/xlsx：doc_extract 表格抽取"})
manifest.append({"group": "04_media_inventory", "file": f"{len(arc)} archives", "bytes": sum(p.stat().st_size for p in arc),
                 "source_file": "local machine scan", "note": "zip 资产盘点"})

# ---------- manifest + README ----------
import csv as _csv
with open(ROOT / "manifest.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = _csv.DictWriter(fh, fieldnames=["group", "file", "bytes", "source_file", "note"])
    w.writeheader()
    for row in manifest:
        w.writerow(row)

total = sum(r["bytes"] for r in manifest if r["bytes"])
print(f"manifest rows: {len(manifest)}  total: {total/1024/1024:.1f} MB")
for g in sorted(GROUPS):
    files = [r for r in manifest if r["group"].startswith(g)]
    print(f"  {g:<20} {len(files):>2} items  {sum(r['bytes'] for r in files)/1024/1024:>8.1f} MB  {GROUPS[g]}")
