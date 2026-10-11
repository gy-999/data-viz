
import gzip, csv, json, os, re, sqlite3, subprocess, sys
from collections import Counter
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

args = sys.argv[1:]
data_dir, out_dir, title, unit, view_name = args[0], args[1], args[2], args[3], args[4]

HERE = Path(__file__).resolve().parent
_vd_path = Path(os.environ.get("VIEW_DICT", HERE.parent / "output" / "well_dashboard_v2" / "view_dict.json"))
vd = json.load(open(_vd_path, encoding="utf-8")) if _vd_path.exists() else {}
vdict = vd.get(view_name, {})
memo = vdict.get("LIFECYCLESTATUS", {}).get("memo", "")
LIFE = {}
if ":" in memo:
    for part in memo.replace("，", ",").split(","):
        p = part.split(":")
        if len(p) == 2 and p[0].strip().isdigit(): LIFE[p[0].strip()] = p[1].strip()
if not LIFE: LIFE = {"1":"规划","2":"设计","3":"工程","4":"在网","5":"维护","6":"退网"}
print("LIFE codes:", LIFE)

os.makedirs(out_dir, exist_ok=True)
os.makedirs(os.path.join(out_dir, "artifacts"), exist_ok=True)

print("[1] loading", data_dir)
all_rows = []; headers = []
for f in sorted(Path(data_dir).glob("*.CSV.GZ")):
    with gzip.open(f, "rt", encoding="utf-8-sig") as fh:
        rd = csv.reader(fh, delimiter="|")
        h = next(rd)
        if not headers: headers = h
        for row in rd: all_rows.append(row)
total = len(all_rows)
print("  ", total, "rows x", len(headers), "cols")

idx = {h: i for i, h in enumerate(headers)}
def colv(name):
    i = idx.get(name, -1)
    return [(r[i].strip() if i < len(r) else "") for r in all_rows] if i >= 0 else None

c_life = Counter()
for k, v in Counter(colv("LIFECYCLESTATUS")).items():
    c_life[LIFE.get(k, "码"+k+"(待确认)") if k else "(空)"] += v

ZJ = ["杭州","宁波","温州","嘉兴","湖州","绍兴","金华","衢州","舟山","台州","丽水"]
CITY_RE = re.compile("(" + "|".join(ZJ) + ")")
AFTER = {c: re.compile(c + "([\\u4e00-\\u9fa5]{1,6}?[区县])") for c in ZJ}
BLACK = ("小区","园区","社区","矿区","库区","校区")
names = colv("NAME")
c_city = Counter(); c_county = Counter(); city_l = []; county_l = []
for n in names:
    n2 = re.sub(r"^[^\\u4e00-\\u9fa5]*", "", n or "")
    m = CITY_RE.search(n2); cy = (m.group(1) + "市") if m else ""
    ct = ""
    if cy:
        m2 = AFTER[cy[:-1]].search(n2)
        if m2 and not m2.group(1).endswith(BLACK): ct = m2.group(1)
    city_l.append(cy); county_l.append(ct)
    if cy: c_city[cy] += 1
    if ct: c_county[ct] += 1

years = Counter(v[:4] for v in (colv("ONLINEDATE") or []) if v)
has_coord = sum(1 for a, b in zip(colv("LONGITUDE") or [], colv("LATITUDE") or []) if a and b)
zaiwang = c_life.get("在网", 0)
zwp = round(zaiwang / total * 100, 1) if total else 0
print("  在网:", zaiwang, "=", zwp, "% | cities:", len(c_city))

print("[2] warehouse...")
db = os.path.join(out_dir, "warehouse.db")
if os.path.exists(db): os.remove(db)
conn = sqlite3.connect(db); cur = conn.cursor()
cur.execute("CREATE TABLE ads_summary (total_cnt INTEGER, zaiwang_cnt INTEGER, zaiwang_pct REAL, city_cnt INTEGER, county_cnt INTEGER, has_coord INTEGER)")
cur.execute("INSERT INTO ads_summary VALUES (?,?,?,?,?,?)", (total, zaiwang, zwp, len(c_city), len(c_county), has_coord))
def ads(table, dim, counter, top=20):
    cur.execute("DROP TABLE IF EXISTS " + table)
    cur.execute("CREATE TABLE " + table + " (" + dim + " TEXT, cnt INTEGER)")
    cur.executemany("INSERT INTO " + table + " VALUES (?,?)", counter.most_common(top))
ads("ads_lifecycle", "lifecyclestatus", c_life)
ads("ads_city", "city", c_city, top=12)
ads("ads_county", "county", c_county, top=12)
ads("ads_year", "yr", Counter({k: years[k] for k in sorted(years) if k.isdigit() and 1900 < int(k) < 2027}), top=20)
cur.execute("DROP TABLE IF EXISTS ads_codebook")
cur.execute("CREATE TABLE ads_codebook (fld TEXT, val TEXT, meaning TEXT, basis TEXT)")
cbrows = [("生命周期状态", k, v, "官方备注") for k, v in LIFE.items()]
cbrows.append(("覆盖地市", "解析", "从名称解析浙江地市", "拍板口径"))
cur.executemany("INSERT INTO ads_codebook VALUES (?,?,?,?)", cbrows)
detail_cols = [c for c in ["ID","NAME","LIFECYCLESTATUS","ONLINEDATE","LONGITUDE","LATITUDE","NFCID"] if c in idx]
cur.execute("DROP TABLE IF EXISTS dwd_res")
cur.execute("CREATE TABLE dwd_res (" + ", ".join('"' + c + '" TEXT' for c in detail_cols) + ", CITY_P TEXT, COUNTY_P TEXT)")
ph = ",".join(["?"]*(len(detail_cols)+2))
cn = ",".join('"' + c + '"' for c in detail_cols) + ",CITY_P,COUNTY_P"
di = [idx[c] for c in detail_cols]
ns = min(50000, total)
batch = []
for r, cy, ct in zip(all_rows[:ns], city_l[:ns], county_l[:ns]):
    batch.append([(r[i].strip() if i < len(r) else "") for i in di] + [cy, ct])
    if len(batch) >= 5000:
        cur.executemany("INSERT INTO dwd_res (" + cn + ") VALUES (" + ph + ")", batch); batch = []
if batch: cur.executemany("INSERT INTO dwd_res (" + cn + ") VALUES (" + ph + ")", batch)
conn.commit(); conn.close()
print("  warehouse done, detail:", ns)

print("[3] calibers + config...")
FENCE = chr(96)*3
cal = []
def card(n, title, pairs):
    cal.append("## 口径卡 " + str(n) + "：" + title)
    cal.append(FENCE + "yaml")
    for k, v in pairs: cal.append(k + ": " + v)
    cal.append("更新周期: 一次性快照（2026-09-14 分片）"); cal.append(FENCE); cal.append("")
card(1, title.split("·")[0].strip() + "总数", [("指标名","总数"), ("分子","全部记录行"), ("分母","无"), ("只算什么","官方视图全字段"), ("不算什么","无"), ("业务方确认","GuoYun 2026-10-10（默认口径）")])
card(2, "在网占比", [("指标名","在网占比"), ("分子","生命周期=在网（官方码值）"), ("分母","全部记录"), ("只算什么","官方码值翻译"), ("不算什么","无"), ("业务方确认","GuoYun 2026-10-10（默认口径）")])
card(3, "覆盖地市", [("指标名","覆盖地市"), ("分子","名称解析出的浙江地市数"), ("分母","11"), ("只算什么","名称含地市名"), ("不算什么","无法解析"), ("业务方确认","GuoYun 2026-10-10（默认口径）")])
with open(os.path.join(out_dir, "artifacts", "口径卡.md"), "w", encoding="utf-8") as f:
    f.write(chr(10).join(cal))

cfg = {
    "version": 2, "title": title,
    "metrics": [
        {"id": "total", "name": "资源总数", "direction": "up", "unit": unit,
         "caliber": "总数", "source": {"table": "ads_summary", "column": "total_cnt"}},
        {"id": "zw", "name": "在网占比", "direction": "up", "unit": "%", "caliber": "在网占比",
         "source": {"table": "ads_summary", "column": "zaiwang_pct"}},
        {"id": "cityc", "name": "覆盖地市", "direction": "up", "unit": "个", "caliber": "覆盖地市",
         "source": {"table": "ads_summary", "column": "city_cnt"}},
        {"id": "coord", "name": "含坐标", "direction": "up", "unit": unit,
         "source": {"table": "ads_summary", "column": "has_coord"}},
    ],
    "components": [
        {"id": "k1", "type": "kpi", "metric": "total"},
        {"id": "k2", "type": "kpi", "metric": "zw"},
        {"id": "k3", "type": "kpi", "metric": "cityc"},
        {"id": "k4", "type": "kpi", "metric": "coord"},
        {"id": "h1", "type": "heading", "content": "一、构成分析（生命周期码值已按官方备注翻译）"},
        {"id": "p1", "type": "pie", "metric": "cnt", "table": "ads_lifecycle", "dimension": "lifecyclestatus", "label": "生命周期状态构成", "order": "cnt DESC"},
        {"id": "b1", "type": "bar", "metric": "cnt", "table": "ads_city", "dimension": "city", "label": "地市分布（解析自名称）", "order": "cnt DESC"},
        {"id": "b2", "type": "bar", "metric": "cnt", "table": "ads_county", "dimension": "county", "label": "区县分布 Top12（解析自名称）", "order": "cnt DESC"},
        {"id": "b3", "type": "bar", "metric": "cnt", "table": "ads_year", "dimension": "yr", "label": "入网年份分布", "order": "yr ASC"},
        {"id": "h2", "type": "heading", "content": "二、码值字典与数据说明"},
        {"id": "tb", "type": "table", "table": "ads_codebook", "columns": ["fld","val","meaning","basis"], "top": 8, "title": "码值字典（官方备注）"},
        {"id": "tx", "type": "text", "content": "数据说明：来源 " + data_dir + "，共 " + format(total, ",") + " 条 × " + str(len(headers)) + " 字段，字段中文名取自《4个哑资源视图1204》官方字典。生命周期官方码值：" + memo[:40] + "。如何转发：单文件离线网页，微信/邮件直发，双击浏览器打开；L3 明细为前 " + format(ns, ",") + " 行抽样。"},
    ],
    "drill": {
        "l2": {"dimensions": [
            {"table": "ads_lifecycle", "dimension": "lifecyclestatus", "label": "按生命周期", "order": "cnt DESC"},
            {"table": "ads_city", "dimension": "city", "label": "按地市", "order": "cnt DESC"},
            {"table": "ads_county", "dimension": "county", "label": "按区县", "order": "cnt DESC"}
        ]},
        "l3": {"table": "dwd_res", "columns": detail_cols,
               "dimension_map": {"lifecyclestatus": "LIFECYCLESTATUS", "city": "CITY_P", "county": "COUNTY_P"},
               "limit": 200}
    }
}
import yaml
with open(os.path.join(out_dir, "dashboard.config.yaml"), "w", encoding="utf-8") as f:
    yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

print("[4] render...")
rp = str(HERE / "render_universal_dashboard.py")
res = subprocess.run([sys.executable, "-X", "utf8", rp, out_dir],
                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
print("  exit:", res.returncode)
if res.returncode != 0:
    print("ERR:", (res.stderr or "")[-600:]); sys.exit(1)
if res.stdout: print(" ", res.stdout.strip()[:150])

chk = subprocess.run([sys.executable, "-X", "utf8",
    str(HERE / "dashboard_check.py"),
    os.path.join(out_dir, "dashboard.html")],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
print(chk.stdout.strip())
