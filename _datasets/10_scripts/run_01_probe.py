"""data-viz 正式测试 · 第 1 步：探源与质量体检（本地代码扫描 + 待 AI 拍板的口径问题）"""
import csv
import json
import pathlib
from collections import Counter

DATA = pathlib.Path(r"D:\Claude cade\data\_datasets\03_text_dirty\chinese_orders_gbk.csv")
OUT = pathlib.Path(__file__).resolve().parent.parent / "09_dashboards" / "_probe"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 78)
print("步骤 1/3  探源六项 · 编码级联")
print("=" * 78)
raw = DATA.read_bytes()
enc_used = None
for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
    try:
        raw.decode(enc)
        enc_used = enc
        print(f"  {enc:<10} OK   <- 采用")
        break
    except UnicodeDecodeError:
        print(f"  {enc:<10} FAIL (UnicodeDecodeError)")

with open(DATA, encoding=enc_used, newline="") as fh:
    rows = list(csv.DictReader(fh))
cols = list(rows[0].keys())
print(f"\n行数 {len(rows):,} | 列数 {len(cols)}")

print("\n" + "=" * 78)
print("步骤 1/3  探源六项 · 空值与伪装空值")
print("=" * 78)
for c in cols:
    blank = sum(1 for r in rows if str(r[c]).strip() == "")
    none_like = sum(1 for r in rows if str(r[c]).strip().lower() in ("none", "null", "\\n", "nan"))
    if blank or none_like:
        print(f"  {c:<8} 空串 {blank:>5} ({blank/len(rows)*100:>5.1f}%)   字面None/NULL {none_like:>5}")

print("\n" + "=" * 78)
print("步骤 1/3  探源六项 · 枚举、重复、时间")
print("=" * 78)
for c in ("客户类型", "产品类别", "省份", "订单状态" if "订单状态" in cols else "折扣"):
    dist = Counter(str(r[c]) for r in rows)
    print(f"  {c:<8} {len(dist):>3} 个取值: {dict(dist.most_common(6))}")

oid = Counter(r["订单号"] for r in rows)
dup_rows = sum(v - 1 for v in oid.values() if v > 1)
print(f"\n  订单号: 唯一 {len(oid):,} / 总行 {len(rows):,} -> {dup_rows:,} 行为重复订单号")

dates = Counter(r["订单日期"] for r in rows)
print(f"  订单日期: {len(dates)} 个不同值，Top5 {dates.most_common(5)}")
years = Counter(r["订单日期"][:4] for r in rows if r["订单日期"][:4].isdigit())
print(f"  年份分布: {dict(sorted(years.items()))}")

# 数值列体检
def num(v):
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return None

for c in ("销售额", "数量", "利润"):
    vals = [num(r[c]) for r in rows]
    bad = sum(1 for v in vals if v is None)
    ok = [v for v in vals if v is not None]
    neg = sum(1 for v in ok if v < 0)
    print(f"  {c:<6} 可解析 {len(ok):>5} / 不可解析 {bad:>4} | 最小 {min(ok):>10.2f} 最大 {max(ok):>10.2f} | 负值 {neg}")

probe = {
    "file": DATA.name,
    "encoding_used": enc_used,
    "rows": len(rows),
    "cols": cols,
    "duplicate_order_rows": dup_rows,
    "unique_orders": len(oid),
    "date_distinct": len(dates),
    "date_top": dates.most_common(5),
    "year_dist": dict(sorted(years.items())),
    "enum": {c: dict(Counter(str(r[c]) for r in rows).most_common(10)) for c in cols},
}
(OUT / "probe_result.json").write_text(json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n[已保存] {OUT / 'probe_result.json'}")
