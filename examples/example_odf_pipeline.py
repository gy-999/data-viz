
import gzip, csv, json, os, re, sqlite3, subprocess, sys, shutil
from collections import Counter
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# 可移植定位：以本文件所在目录为锚点，换机器/换用户名都不用改（v3）
HERE = Path(__file__).resolve().parent

FENCE = chr(96) * 3

# 数据目录：默认占位符，可用环境变量覆盖 ->  $env:DATA_VIZ_DATA_DIR="D:\你的数据\ZJsftp\..."
data_dir = os.environ.get("DATA_VIZ_DATA_DIR", r"D:\\你的数据\\ZJsftp\\IRM_V_ODF_D")
out_dir = os.environ.get("DATA_VIZ_OUT_DIR", str(HERE.parent / "output" / "odf_dashboard"))
os.makedirs(out_dir, exist_ok=True)
os.makedirs(os.path.join(out_dir, "artifacts"), exist_ok=True)
os.makedirs(os.path.join(out_dir, "source-cleaned"), exist_ok=True)

print("[1/8] Loading ODF data...")
all_rows = []; headers = []
for f in sorted(Path(data_dir).glob("*.CSV.GZ")):
    with gzip.open(f, "rt", encoding="utf-8-sig") as fh:
        rd = csv.reader(fh, delimiter="|")
        h = next(rd)
        if not headers: headers = h
        for row in rd: all_rows.append(row)
total = len(all_rows)
print("  ", total, "rows x", len(headers), "cols | files:", len(list(Path(data_dir).glob("*.CSV.GZ"))))

idx = {h: i for i, h in enumerate(headers)}

def colv(name):
    i = idx.get(name, -1)
    return [(r[i].strip() if i < len(r) else "") for r in all_rows] if i >= 0 else None

# official dict（沿用 WELL 案例产出的官方视图字典；没有就先跑 WELL 案例，或跳过字典翻译）
vd = {}
_vd_path = os.path.join(out_dir, "..", "well_dashboard_v2", "view_dict.json")
if os.path.exists(_vd_path):
    vd = json.load(open(_vd_path, encoding="utf-8"))
else:
    print("  [warn] 未找到 view_dict.json，跳过官方字典翻译（可先跑 example_well_pipeline.py 生成）")
odf_dict = vd.get("IRM_V_ODF", {})
LIFE = {"1":"规划","2":"设计","3":"工程","4":"在网","5":"维护","6":"退网"}
for k in ["LIFECYCLESTATUS"]:
    memo = odf_dict.get(k, {}).get("memo", "")
    if memo: print("  官方码值", k, "->", memo[:60])

print("[2/8] 探源六项...")
# 1 rows/cols; 2 null rate incl empty string; 3 enums; 4 duplicate ID; 5 time range+cliff; 6 single-table
probe = {"rows": total, "cols": len(headers), "null_top": [], "enums": {}, "dup_id": 0, "time": {}}
idv = colv("ID")
probe["dup_id"] = total - len(set(idv)) if idv else 0
nulls = {}
for h in headers:
    v = colv(h)
    n = sum(1 for x in v if not x)
    nulls[h] = n
top_null = sorted(nulls.items(), key=lambda x: -x[1])[:8]
probe["null_top"] = [(h, round(n/total*100,1)) for h, n in top_null]
low_card = []
for h in headers:
    v = colv(h)
    u = set(x for x in v if x)
    if 0 < len(u) <= 12 and not re.match(r"^\d{4}-", u.copy().pop() if u else ""):
        low_card.append((h, Counter(v).most_common(8)))
probe["enums"] = low_card[:10]
for tf in ["ONLINEDATE", "CREATEDATE"]:
    v = [x for x in (colv(tf) or []) if x]
    if v: probe["time"][tf] = (min(v)[:10], max(v)[:10])
yr = Counter(v[:4] for v in (colv("ONLINEDATE") or []) if v)
probe["cliff"] = "末年未存满需同期口径" if yr and max(int(k) for k in yr if k.isdigit()) >= 2026 else "无"

print("  空值率Top:", probe["null_top"][:5])
print("  重复ID:", probe["dup_id"], "| 时间:", probe["time"], "| 悬崖:", probe["cliff"])

print("[3/8] Aggregating with official Chinese labels...")
c_life = Counter()
for k, v in Counter(colv("LIFECYCLESTATUS")).items():
    c_life[LIFE.get(k, "码"+k+"(待确认)") if k else "(空)"] += v

ZJ = ["杭州","宁波","温州","嘉兴","湖州","绍兴","金华","衢州","舟山","台州","丽水"]
CITY_RE = re.compile("(" + "|".join(ZJ) + ")")
AFTER = {c: re.compile(c + "([\\u4e00-\\u9fa5]{1,6}?[区县])") for c in ZJ}
BLACK = ("小区","园区","社区","矿区","库区","校区")

names = colv("NAME")
c_city = Counter(); c_county = Counter()
city_list = []; county_list = []
for n in names:
    n2 = re.sub(r"^[^\\u4e00-\\u9fa5]*", "", n or "")
    m = CITY_RE.search(n2)
    cy = (m.group(1) + "市") if m else ""
    ct = ""
    if cy:
        m2 = AFTER[cy[:-1]].search(n2)
        if m2 and not m2.group(1).endswith(BLACK):
            ct = m2.group(1)
    city_list.append(cy); county_list.append(ct)
    if cy: c_city[cy] += 1
    if ct: c_county[ct] += 1

years = Counter(v[:4] for v in (colv("ONLINEDATE") or []) if v)
nfc = Counter()
for v in (colv("NFCID") or []):
    nfc["已贴NFC标签" if v else "未贴NFC标签"] += 1
has_coord = sum(1 for a, b in zip(colv("LONGITUDE") or [], colv("LATITUDE") or []) if a and b)
zaiwang = c_life.get("在网", 0)
zaiwang_pct = round(zaiwang / total * 100, 1) if total else 0
print("  在网:", zaiwang, "=", zaiwang_pct, "% | cities:", len(c_city), "| counties:", len(c_county))

print("[4/8] 源版整理 (source-cleaned)...")
import xlsxwriter
xw = xlsxwriter.Workbook(os.path.join(out_dir, "source-cleaned", "01_ODF_cleaned_sample.xlsx"))
ws = xw.add_worksheet("ODF")
hfmt = xw.add_format({"bold": True, "bg_color": "#4472C4", "font_color": "white", "border": 1})
for j, h in enumerate(headers):
    cn = odf_dict.get(h, {}).get("cn", "")
    ws.write(0, j, (h + " " + cn) if cn else h, hfmt)
    ws.set_column(j, j, min(max(12, len(h) + len(cn)), 30))
for i, r in enumerate(all_rows[:20000], start=1):
    for j in range(len(headers)):
        v = r[j].strip() if j < len(r) else ""
        if v: ws.write_string(i, j, v[:200])
xw.close()
with open(os.path.join(out_dir, "source-cleaned", "02_source-report.md"), "w", encoding="utf-8") as f:
    f.write("# ODF 源版整理报告\n\n")
    f.write("- 来源: IRM_V_ODF_D (" + str(len(list(Path(data_dir).glob('*.CSV.GZ')))) + " 个分片)\n")
    f.write("- 行数: " + format(total, ",") + " x " + str(len(headers)) + " 字段\n")
    f.write("- 重复ID: " + str(probe["dup_id"]) + "\n")
    f.write("- 时间范围: " + json.dumps(probe["time"], ensure_ascii=False) + "\n")
    f.write("- 字段中文名: 取自《4个哑资源视图1204》官方字典\n")
    f.write("- 样例文件: 01_ODF_cleaned_sample.xlsx（前 2 万行，表头=英文名+官方中文名）\n")
print("  source-cleaned done")

print("[5/8] warehouse.db...")
db_path = os.path.join(out_dir, "warehouse.db")
if os.path.exists(db_path): os.remove(db_path)
conn = sqlite3.connect(db_path); cur = conn.cursor()
cur.execute("CREATE TABLE ads_res_summary (total_cnt INTEGER, zaiwang_cnt INTEGER, zaiwang_pct REAL, city_cnt INTEGER, county_cnt INTEGER, has_coord INTEGER, nfc_cnt INTEGER)")
cur.execute("INSERT INTO ads_res_summary VALUES (?,?,?,?,?,?,?)",
            (total, zaiwang, zaiwang_pct, len(c_city), len(c_county), has_coord, nfc.get("已贴NFC标签", 0)))

def make_ads(table, dimcol, counter, top=20):
    cur.execute("DROP TABLE IF EXISTS " + table)
    cur.execute("CREATE TABLE " + table + " (" + dimcol + " TEXT, cnt INTEGER)")
    cur.executemany("INSERT INTO " + table + " VALUES (?,?)", counter.most_common(top))

make_ads("ads_lifecycle", "lifecyclestatus", c_life)
make_ads("ads_city", "city", c_city, top=12)
make_ads("ads_county", "county", c_county, top=12)
make_ads("ads_year", "yr", Counter({k: years[k] for k in sorted(years) if k.isdigit() and 1990 < int(k) < 2027}), top=20)
make_ads("ads_nfc", "nfcstat", nfc)

cur.execute("DROP TABLE IF EXISTS ads_codebook")
cur.execute("CREATE TABLE ads_codebook (fld TEXT, val TEXT, meaning TEXT, basis TEXT)")
cb = [
    ("生命周期状态","1","规划","官方备注"), ("生命周期状态","2","设计","官方备注"),
    ("生命周期状态","3","工程","官方备注"), ("生命周期状态","4","在网","官方备注"),
    ("生命周期状态","5","维护","官方备注"), ("生命周期状态","6","退网","官方备注"),
    ("设备类型","36038","ODF（由数据规律推断）","推断·待确认"),
    ("NFC标签","有值/空","已贴/未贴标签","口径卡"),
]
cur.executemany("INSERT INTO ads_codebook VALUES (?,?,?,?)", cb)

detail_cols = [c for c in ["ID","NAME","LIFECYCLESTATUS","EQUIPMENTTYPE","ONLINEDATE","NFCID","LONGITUDE","LATITUDE","CREATEDATE"] if c in idx]
cur.execute("DROP TABLE IF EXISTS dwd_odf")
cur.execute("CREATE TABLE dwd_odf (" + ", ".join('"'+c+'" TEXT' for c in detail_cols) + ", CITY_P TEXT, COUNTY_P TEXT)")
ph = ",".join(["?"]*(len(detail_cols)+2))
cn = ",".join('"'+c+'"' for c in detail_cols) + ",CITY_P,COUNTY_P"
di = [idx[c] for c in detail_cols]
N_SAMPLE = min(50000, total)
batch = []
for r, cy, ct in zip(all_rows[:N_SAMPLE], city_list[:N_SAMPLE], county_list[:N_SAMPLE]):
    batch.append([(r[i].strip() if i < len(r) else "") for i in di] + [cy, ct])
    if len(batch) >= 5000:
        cur.executemany("INSERT INTO dwd_odf ("+cn+") VALUES ("+ph+")", batch); batch = []
if batch: cur.executemany("INSERT INTO dwd_odf ("+cn+") VALUES ("+ph+")", batch)
conn.commit(); conn.close()
print("  done, detail rows:", N_SAMPLE)

print("[6/8] calibers + config...")
cal = []
def card(n, title, lines):
    cal.append("## 口径卡 " + str(n) + "：" + title)
    cal.append(FENCE + "yaml")
    for k, v in lines: cal.append(k + ": " + v)
    cal.append("更新周期: 一次性快照（2026-09-14 分片）")
    cal.append(FENCE)
    cal.append("")
card(1, "ODF总数", [("指标名","ODF总数"), ("分子","IRM_V_ODF_D 全部记录行"), ("分母","无（总量指标）"), ("只算什么","全部分片记录"), ("不算什么","无")])
card(2, "在网占比", [("指标名","在网占比"), ("分子","生命周期=在网（官方码值4）"), ("分母","全部记录（含空值）"), ("只算什么","官方码值翻译"), ("不算什么","无")])
card(3, "已贴标签数", [("指标名","已贴标签数"), ("分子","NFCID 非空的记录数"), ("分母","ODF总数"), ("只算什么","NFCID 字段非空"), ("不算什么","空白字符串视为未贴")])
card(4, "覆盖地市", [("指标名","覆盖地市"), ("分子","从名称解析出的浙江地市数"), ("分母","浙江 11 地市"), ("只算什么","名称含地市名的记录"), ("不算什么","无法解析地市的记录")])
with open(os.path.join(out_dir, "artifacts", "口径卡.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(cal) + "\n")

cfg = {
    "version": 2,
    "title": "浙江移动 · ODF 光配线架资源分析看板",
    "metrics": [
        {"id": "total", "name": "ODF总数", "direction": "up", "unit": "架", "caliber": "ODF总数",
         "source": {"table": "ads_res_summary", "column": "total_cnt"}},
        {"id": "zw", "name": "在网占比", "direction": "up", "unit": "%", "caliber": "在网占比",
         "source": {"table": "ads_res_summary", "column": "zaiwang_pct"}},
        {"id": "nfc", "name": "已贴标签数", "direction": "up", "unit": "架", "caliber": "已贴标签数",
         "source": {"table": "ads_res_summary", "column": "nfc_cnt"}},
        {"id": "cityc", "name": "覆盖地市", "direction": "up", "unit": "个", "caliber": "覆盖地市",
         "source": {"table": "ads_res_summary", "column": "city_cnt"}},
    ],
    "components": [
        {"id": "k1", "type": "kpi", "metric": "total"},
        {"id": "k2", "type": "kpi", "metric": "zw"},
        {"id": "k3", "type": "kpi", "metric": "nfc"},
        {"id": "k4", "type": "kpi", "metric": "cityc"},
        {"id": "h1", "type": "heading", "content": "一、构成分析（图例均为官方中文名，码值见文末字典）"},
        {"id": "p1", "type": "pie", "metric": "cnt", "table": "ads_lifecycle", "dimension": "lifecyclestatus", "label": "生命周期状态构成", "order": "cnt DESC"},
        {"id": "p2", "type": "pie", "metric": "cnt", "table": "ads_nfc", "dimension": "nfcstat", "label": "NFC 标签覆盖"},
        {"id": "b1", "type": "bar", "metric": "cnt", "table": "ads_city", "dimension": "city", "label": "地市分布（解析自名称）", "order": "cnt DESC"},
        {"id": "b2", "type": "bar", "metric": "cnt", "table": "ads_county", "dimension": "county", "label": "区县分布 Top12（解析自名称）", "order": "cnt DESC"},
        {"id": "b3", "type": "bar", "metric": "cnt", "table": "ads_year", "dimension": "yr", "label": "入网年份分布", "order": "yr ASC"},
        {"id": "h2", "type": "heading", "content": "二、码值字典与数据说明（转发前请读）"},
        {"id": "tb", "type": "table", "table": "ads_codebook", "columns": ["fld","val","meaning","basis"], "top": 10, "title": "码值字典"},
        {"id": "tx", "type": "text", "content": "数据说明：来源 D:/你的数据/ZJsftp/IRM_V_ODF_D，共 " + format(total, ",") + " 条 × " + str(len(headers)) + " 字段，字段中文名取自《4个哑资源视图1204》官方字典。ODF=光纤配线架。生命周期官方码值：1规划/2设计/3工程/4在网/5维护/6退网。如何转发：本文件为单文件离线网页，微信/邮件直发，对方双击浏览器打开即可；L3 明细为前 " + format(N_SAMPLE, ",") + " 行抽样。配套《ODF数据分析报告.docx》含完整口径卡与结论。"},
    ],
    "drill": {
        "l2": {"dimensions": [
            {"table": "ads_lifecycle", "dimension": "lifecyclestatus", "label": "按生命周期", "order": "cnt DESC"},
            {"table": "ads_city", "dimension": "city", "label": "按地市", "order": "cnt DESC"},
            {"table": "ads_county", "dimension": "county", "label": "按区县", "order": "cnt DESC"}
        ]},
        "l3": {
            "table": "dwd_odf",
            "columns": detail_cols,
            "dimension_map": {"lifecyclestatus": "LIFECYCLESTATUS", "city": "CITY_P", "county": "COUNTY_P"},
            "limit": 200
        }
    }
}
import yaml
with open(os.path.join(out_dir, "dashboard.config.yaml"), "w", encoding="utf-8") as f:
    yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

print("[7/8] FIELD_CN + render...")
rp = str(HERE.parent / "scripts" / "render_universal_dashboard.py")
src = open(rp, encoding="utf-8").read()
if "ODF 补充字典" not in src:
    add = ('    # ---- ODF 补充字典 ----\n'
           '    "EQUIPMENTTYPE": "设备类型", "equipmenttype": "设备类型",\n'
           '    "total_cnt": "资源总数", "city_cnt": "覆盖地市数",\n'
           '    "nfcstat": "NFC标签状态", "county_cnt": "覆盖区县数", "has_coord": "含坐标数",\n')
    # 插到 FIELD_CN 字典开头：不依赖任何数据集专属行（WELL 案例的正则重写会吞掉那些锚点）
    marker = "FIELD_CN = {\n"
    i = src.find(marker)
    if i < 0:
        print("  [warn] 未找到 FIELD_CN，跳过 ODF 字典补录"); sys.exit(1)
    src = src[:i + len(marker)] + add + src[i + len(marker):]
    open(rp, "w", encoding="utf-8").write(src)
    print("  FIELD_CN + ODF entries")

res = subprocess.run([sys.executable, "-X", "utf8", rp, out_dir],
                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
print("  render exit:", res.returncode)
if res.returncode != 0:
    print("ERR:", (res.stderr or "")[-1000:]); sys.exit(1)
if res.stdout: print(" ", res.stdout.strip()[:160])

html_path = os.path.join(out_dir, "dashboard.html")
chk = subprocess.run([sys.executable, "-X", "utf8",
    str(HERE.parent / "scripts" / "dashboard_check.py"), html_path],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
print(chk.stdout.strip())

h = open(html_path, encoding="utf-8").read()
mm = re.search(r"const DATA = (\{.+?\});\r?\n", h, re.S)
d = json.loads(mm.group(1))
dom = d["domains"][0]
for c in dom["components"]:
    if c.get("type") == "kpi":
        print("KPI:", c["data"].get("name"), "=", c["data"].get("value"))
for c in dom["components"]:
    if c.get("type") == "pie" and "生命周期" in str(c["data"].get("title","")):
        print("PIE:", [(s["label"], s["value"]) for s in c["data"]["slices"][:5]])
print("l2dims:", len(d.get("drill",{}).get("l2dims",[])), "| l3:", "PRESENT" if d.get("drill",{}).get("l3") else "null")
print("SIZE:", round(len(h)/1024), "KB")

shallow = str(HERE.parent / "ODF数据看板.html")
shutil.copyfile(html_path, shallow)
print("COPIED ->", shallow)
