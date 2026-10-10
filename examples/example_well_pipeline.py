
import gzip, csv, json, os, re, sqlite3, subprocess, sys, shutil
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FENCE = chr(96) * 3

data_dir = r"D:\\数据\\ZJsftp\\IRM_IV_WELL_D"
out_dir = r"D:\\study\\NewPeople\\data\\data-viz\\output\\well_dashboard_v2"
os.makedirs(out_dir, exist_ok=True)
os.makedirs(os.path.join(out_dir, "artifacts"), exist_ok=True)

print("[1/7] Loading FULL data...")
all_rows = []; headers = []
for f in sorted(Path(data_dir).glob("*.CSV.GZ")):
    with gzip.open(f, "rt", encoding="utf-8-sig") as fh:
        rd = csv.reader(fh, delimiter="|")
        h = next(rd)
        if not headers: headers = h
        for row in rd: all_rows.append(row)
print("  ", len(all_rows), "rows")

idx = {h: i for i, h in enumerate(headers)}

def colv(name):
    i = idx.get(name, -1)
    return [(r[i].strip() if i < len(r) else "") for r in all_rows] if i >= 0 else None

LIFE = {"1":"规划","2":"设计","3":"工程","4":"在网","5":"维护","6":"退网"}

ZJ = ["杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水"]
CITY_RE = re.compile("(" + "|".join(ZJ) + ")市")
AFTER = {c: re.compile(c + "市([\u4e00-\u9fa5]{1,6}?[区县])") for c in ZJ}
BLACK = ("小区", "园区", "社区", "矿区", "库区", "校区")

def parse_city(name):
    n = re.sub(r"^[^\u4e00-\u9fa5]*", "", name or "")
    m = CITY_RE.search(n)
    return (m.group(1) + "市") if m else ""

def parse_county(name, city):
    if city:
        m = AFTER[city[:-1]].search(name or "")
        if m:
            cand = m.group(1)
            if not cand.endswith(BLACK):
                return cand
    return ""

print("[2/7] Aggregating with Chinese labels...")
c_life = Counter()
for k, v in Counter(colv("LIFECYCLESTATUS")).items():
    c_life[LIFE.get(k, "码"+k+"(待确认)") if k else "(空)"] += v
c_vc = Counter(("类别"+k if k else "(空)") for k in colv("VIRTUALCATEGORY"))
c_pc = Counter(("性质"+k if k else "(空)") for k in colv("PROPERTYCATEGORY"))

names = colv("NAME")
c_city = Counter(); c_county = Counter()
city_list = []; county_list = []
for n in names:
    cy = parse_city(n); ct = parse_county(n, cy)
    city_list.append(cy); county_list.append(ct)
    if cy: c_city[cy] += 1
    if ct: c_county[ct] += 1

c_fw = Counter(colv("ISFIRSTWELL"))
c_mf = Counter(colv("ISMARKEDFORBIDDEN"))
lng = colv("LONGITUDE"); lat = colv("LATITUDE")
has_loc = sum(1 for a, b in zip(lng, lat) if a and b)
years = Counter(v[:4] for v in colv("ONLINEDATE") if v)
zaiwang = c_life.get("在网", 0)
total = len(all_rows)
zaiwang_pct = round(zaiwang / total * 100, 1)
print("  在网:", zaiwang, "=", zaiwang_pct, "% | cities:", len(c_city), "counties:", len(c_county))

print("[3/7] warehouse.db...")
db_path = os.path.join(out_dir, "warehouse.db")
if os.path.exists(db_path): os.remove(db_path)
conn = sqlite3.connect(db_path); cur = conn.cursor()
cur.execute("CREATE TABLE ads_well_summary (total_wells INTEGER, zaiwang_cnt INTEGER, zaiwang_pct REAL, county_parsed_cnt INTEGER, has_location INTEGER, city_parsed_cnt INTEGER)")
cur.execute("INSERT INTO ads_well_summary VALUES (?,?,?,?,?,?)", (total, zaiwang, zaiwang_pct, len(c_county), has_loc, len(c_city)))

def make_ads(table, dimcol, counter, top=20):
    cur.execute("DROP TABLE IF EXISTS " + table)
    cur.execute("CREATE TABLE " + table + " (" + dimcol + " TEXT, cnt INTEGER)")
    cur.executemany("INSERT INTO " + table + " VALUES (?,?)", counter.most_common(top))

make_ads("ads_lifecycle", "lifecyclestatus", c_life)
make_ads("ads_property_cat", "propertycategory", c_pc)
make_ads("ads_virtual_cat", "virtualcategory", c_vc)
make_ads("ads_city", "city", c_city, top=15)
make_ads("ads_county", "county", c_county, top=15)
make_ads("ads_year", "yr", Counter({k: years[k] for k in sorted(years) if k.isdigit() and 1990 < int(k) < 2027}), top=30)

cur.execute("DROP TABLE IF EXISTS ads_forbidden")
cur.execute("CREATE TABLE ads_forbidden (forbidden TEXT, cnt INTEGER)")
cur.executemany("INSERT INTO ads_forbidden VALUES (?,?)",
    [("否(码2)", c_mf.get("2",0)), ("是(码1)", c_mf.get("1",0)), ("(空)", c_mf.get("",0))])
cur.execute("DROP TABLE IF EXISTS ads_firstwell")
cur.execute("CREATE TABLE ads_firstwell (firstwell TEXT, cnt INTEGER)")
cur.executemany("INSERT INTO ads_firstwell VALUES (?,?)",
    [("否(码2)", c_fw.get("2",0)), ("是(码1)", c_fw.get("1",0)), ("(空)", c_fw.get("",0))])

cur.execute("DROP TABLE IF EXISTS ads_codebook")
cur.execute("CREATE TABLE ads_codebook (fld TEXT, val TEXT, meaning TEXT, basis TEXT)")
cb = [
    ("生命周期状态","1","规划","官方备注"), ("生命周期状态","2","设计","官方备注"),
    ("生命周期状态","3","工程","官方备注"), ("生命周期状态","4","在网","官方备注"),
    ("生命周期状态","5","维护","官方备注"), ("生命周期状态","6","退网","官方备注"),
    ("是否局前井","1","是(推断)","推断·待确认"), ("是否局前井","2","否(推断)","推断·待确认"),
    ("是否标记禁用","1","是(推断)","推断·待确认"), ("是否标记禁用","2","否(推断)","推断·待确认"),
    ("显示类别","1/2/5/6/7","含义未提供","待业务确认"),
    ("产权性质","1/3/5/7/8","含义未提供","待业务确认"),
    ("所属省","1","含义未提供","待业务确认"),
    ("入网时间","按年聚合","取日期前4位","可靠"),
]
cur.executemany("INSERT INTO ads_codebook VALUES (?,?,?,?)", cb)

detail_cols = ["ID","NAME","LIFECYCLESTATUS","VIRTUALCATEGORY","PROPERTYCATEGORY","PROVINCE_ID","COUNTY_ID","ONLINEDATE","LONGITUDE","LATITUDE","NFCID","CREATEDATE"]
cur.execute("DROP TABLE IF EXISTS dwd_well")
cur.execute("CREATE TABLE dwd_well (" + ", ".join('"'+c+'" TEXT' for c in detail_cols) + ", CITY_P TEXT, COUNTY_P TEXT)")
ph = ",".join(["?"]*(len(detail_cols)+2))
cn = ",".join('"'+c+'"' for c in detail_cols) + ",CITY_P,COUNTY_P"
di = [idx[c] for c in detail_cols]
batch = []
for r, cy, ct in zip(all_rows[:50000], city_list[:50000], county_list[:50000]):
    batch.append([(r[i].strip() if i < len(r) else "") for i in di] + [cy, ct])
    if len(batch) >= 5000:
        cur.executemany("INSERT INTO dwd_well ("+cn+") VALUES ("+ph+")", batch); batch = []
if batch: cur.executemany("INSERT INTO dwd_well ("+cn+") VALUES ("+ph+")", batch)
conn.commit(); conn.close()
print("  warehouse done")

print("[4/7] calibers + config...")
cal = []
cal.append("## 口径卡 1：总井数")
cal.append(FENCE + "yaml")
cal.append("指标名: 总井数")
cal.append("分子: IRM_IV_WELL_D 全部记录行")
cal.append("分母: 无（总量指标）")
cal.append("只算什么: 7 个 CSV.GZ 分片（2026-09-14 导出）的全部 1,409,711 行")
cal.append("不算什么: 无")
cal.append("更新周期: 一次性快照")
cal.append(FENCE)
cal.append("")
cal.append("## 口径卡 2：在网占比")
cal.append(FENCE + "yaml")
cal.append("指标名: 在网占比")
cal.append("分子: 生命周期状态=在网（官方码值4）的记录数")
cal.append("分母: 全部记录（含生命周期为空的记录）")
cal.append("只算什么: 生命周期按官方备注翻译（1规划/2设计/3工程/4在网/5维护/6退网）")
cal.append("不算什么: 无（空值保留在分母）")
cal.append("更新周期: 一次性快照")
cal.append(FENCE)
cal.append("")
cal.append("## 口径卡 3：在网井数")
cal.append(FENCE + "yaml")
cal.append("指标名: 在网井数")
cal.append("分子: 生命周期状态=在网（官方码值4）的记录数")
cal.append("分母: 总井数 1,409,711")
cal.append("只算什么: 生命周期按官方备注翻译")
cal.append("不算什么: 规划/设计/工程/维护/退网及空值")
cal.append("更新周期: 一次性快照")
cal.append(FENCE)
cal.append("")
cal.append("## 口径卡 4：含坐标井")
cal.append(FENCE + "yaml")
cal.append("指标名: 含坐标井")
cal.append("分子: 经度和纬度均非空的记录数")
cal.append("分母: 总井数")
cal.append("只算什么: LONGITUDE 与 LATITUDE 同时非空")
cal.append("不算什么: 无")
cal.append("更新周期: 一次性快照")
cal.append(FENCE)
os.makedirs(os.path.join(out_dir, "artifacts"), exist_ok=True)
with open(os.path.join(out_dir, "artifacts", "口径卡.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(cal) + "\n")

cfg = {
    "version": 2,
    "title": "浙江移动 · 管线井（WELL）资源分析看板",
    "metrics": [
        {"id": "total",  "name": "管线井总数", "direction": "up", "unit": "座", "caliber": "总井数",
         "source": {"table": "ads_well_summary", "column": "total_wells"}},
        {"id": "zw",     "name": "在网占比",  "direction": "up", "unit": "%",  "caliber": "在网占比",
         "source": {"table": "ads_well_summary", "column": "zaiwang_pct"}},
        {"id": "zwcnt", "name": "在网井数", "direction": "up", "unit": "座", "caliber": "在网井数", "source": {"table": "ads_well_summary", "column": "zaiwang_cnt"}},
        {"id": "loc",    "name": "含坐标井",  "direction": "up", "unit": "座", "caliber": "含坐标井",
         "source": {"table": "ads_well_summary", "column": "has_location"}},
    ],
    "components": [
        {"id": "k1", "type": "kpi", "metric": "total"},
        {"id": "k2", "type": "kpi", "metric": "zw"},
        {"id": "k3", "type": "kpi", "metric": "zwcnt"},
        {"id": "k4", "type": "kpi", "metric": "loc"},
        {"id": "h1", "type": "heading", "content": "一、构成分析（图例均为官方中文名，码值含义见文末字典）"},
        {"id": "p1", "type": "pie", "metric": "cnt", "table": "ads_lifecycle", "dimension": "lifecyclestatus", "label": "生命周期状态构成", "order": "cnt DESC"},
        {"id": "p2", "type": "pie", "metric": "cnt", "table": "ads_property_cat", "dimension": "propertycategory", "label": "产权性质构成（码值待确认）"},
        {"id": "b1", "type": "bar", "metric": "cnt", "table": "ads_city", "dimension": "city", "label": "地市分布（解析自井名称）", "order": "cnt DESC", "top": 12},
        {"id": "b2", "type": "bar", "metric": "cnt", "table": "ads_virtual_cat", "dimension": "virtualcategory", "label": "显示类别分布（码值待确认）"},
        {"id": "p3", "type": "pie", "metric": "cnt", "table": "ads_firstwell", "dimension": "firstwell", "label": "是否局前井"},
        {"id": "p4", "type": "pie", "metric": "cnt", "table": "ads_forbidden", "dimension": "forbidden", "label": "是否标记禁用"},
        {"id": "b3", "type": "bar", "metric": "cnt", "table": "ads_county", "dimension": "county", "label": "区县分布 Top12（解析自井名称）", "order": "cnt DESC", "top": 12},
        {"id": "b4", "type": "bar", "metric": "cnt", "table": "ads_year", "dimension": "yr", "label": "入网年份分布（按入网时间聚合）", "order": "yr ASC", "top": 20},
        {"id": "h2", "type": "heading", "content": "二、码值字典与数据说明（发给同事前请先读这里）"},
        {"id": "tb", "type": "table", "table": "ads_codebook", "columns": ["fld","val","meaning","basis"], "top": 15, "title": "码值字典（官方备注 + 待确认项）"},
        {"id": "tx", "type": "text", "content": "数据说明：来源 D:/数据/ZJsftp/IRM_IV_WELL_D（7 个 CSV.GZ 分片，2026-09-14 导出），共 1,409,711 条 × 130 字段，字段中文名取自《4个哑资源视图1204》官方字典。如何解读：生命周期状态按官方备注翻译（1规划/2设计/3工程/4在网/5维护/6退网），本库 93.4% 在网；地市/区县分布从井名称解析真实地名；显示类别、产权性质的码值系统未提供含义，需业务方确认后更新码值字典重出看板。如何转发：本文件为单文件离线网页，直接用微信/邮件发送，对方双击用浏览器打开即可，无需安装软件；L3 下钻明细基于前 5 万行抽样。"},
    ],
    "drill": {
        "l2": {"dimensions": [
            {"table": "ads_lifecycle", "dimension": "lifecyclestatus", "label": "按生命周期", "order": "cnt DESC"},
            {"table": "ads_city", "dimension": "city", "label": "按地市", "order": "cnt DESC"},
            {"table": "ads_county", "dimension": "county", "label": "按区县", "order": "cnt DESC"},
            {"table": "ads_property_cat", "dimension": "propertycategory", "label": "按产权性质", "order": "cnt DESC"}
        ]},
        "l3": {
            "table": "dwd_well",
            "columns": ["ID","NAME","LIFECYCLESTATUS","VIRTUALCATEGORY","CITY_P","COUNTY_P","ONLINEDATE","NFCID"],
            "dimension_map": {
                "lifecyclestatus": "LIFECYCLESTATUS",
                "virtualcategory": "VIRTUALCATEGORY",
                "propertycategory": "PROPERTYCATEGORY",
                "city": "CITY_P",
                "county": "COUNTY_P"
            },
            "limit": 200
        }
    }
}
import yaml
with open(os.path.join(out_dir, "dashboard.config.yaml"), "w", encoding="utf-8") as f:
    yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

print("[5/7] FIELD_CN official names...")
rp = r"D:\\study\\NewPeople\\data\\data-viz\\scripts\\render_universal_dashboard.py"
src = open(rp, encoding="utf-8").read()
NEW = "    # ---- WELL 数据集字段字典 v2（官方中文名来自《4个哑资源视图1204》）----\n"
NEW += '    "ID": "标识", "NAME": "名称", "CODE": "编码", "NFCID": "NFC标签",\n'
NEW += '    "LIFECYCLESTATUS": "生命周期状态", "VIRTUALCATEGORY": "显示类别",\n'
NEW += '    "PROPERTYCATEGORY": "产权性质", "PROVINCE_ID": "所属省", "COUNTY_ID": "所属区县",\n'
NEW += '    "PREFECTURE_ID": "所属地市", "ONLINEDATE": "入网时间", "LONGITUDE": "经度",\n'
NEW += '    "LATITUDE": "纬度", "CREATEDATE": "创建时间", "CITY_P": "地市(解析)", "COUNTY_P": "区县(解析)",\n'
NEW += '    "lifecyclestatus": "生命周期状态", "virtualcategory": "显示类别",\n'
NEW += '    "propertycategory": "产权性质", "city": "地市(解析)", "county": "区县(解析)",\n'
NEW += '    "forbidden": "是否标记禁用", "firstwell": "是否局前井",\n'
NEW += '    "fld": "字段", "val": "码值", "meaning": "含义", "basis": "依据",\n'
NEW += '    "cnt": "数量", "yr": "入网年份", "total_wells": "管线井总数",\n'
NEW += '    "zaiwang_cnt": "在网数量", "zaiwang_pct": "在网占比",\n'
NEW += '    "county_parsed_cnt": "覆盖区县数", "has_location": "含坐标井数", "city_parsed_cnt": "覆盖地市数",\n'
m = re.search(r"    # ---- WELL 数据集字段字典.*?\n(?=\S)", src, re.S)
if m:
    src = src[:m.start()] + NEW + "\n" + src[m.end():]
else:
    i = src.find("FIELD_CN = {\n")
    src = src[:i+len("FIELD_CN = {\n")] + "\n" + NEW + src[i+len("FIELD_CN = {\n"):]
open(rp, "w", encoding="utf-8").write(src)
print("  patched")

print("[6/7] Rendering...")
res = subprocess.run([sys.executable, "-X", "utf8", rp, out_dir],
                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
print("  exit:", res.returncode)
if res.stdout: print(" ", res.stdout.strip()[:200])
if res.returncode != 0:
    print("ERR:", (res.stderr or "")[-1200:]); sys.exit(1)

html_path = os.path.join(out_dir, "dashboard.html")
print("[7/7] Gate + verify...")
chk = subprocess.run([sys.executable, "-X", "utf8",
    r"D:\\study\\NewPeople\\data\\data-viz\\scripts\\dashboard_check.py", html_path],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
print(chk.stdout.strip())

h = open(html_path, encoding="utf-8").read()
mm = re.search(r"const DATA = (\{.+?\});\r?\n", h, re.S)
d = json.loads(mm.group(1))
dom = d["domains"][0]
for c in dom["components"]:
    if c.get("type") == "kpi":
        print("KPI:", c["data"].get("name"), "=", c["data"].get("value"), "| 口径分子:", str((c["data"].get("caliber") or {}).get("分子","无"))[:24])
for c in dom["components"]:
    if c.get("type") == "pie" and "生命周期" in str(c["data"].get("title","")):
        print("PIE:", [(s["label"], s["value"]) for s in c["data"]["slices"][:4]])
print("l2dims:", len(d.get("drill",{}).get("l2dims",[])), "| l3:", "PRESENT" if d.get("drill",{}).get("l3") else "null")
print("SIZE:", round(len(h)/1024), "KB")

shallow = r"D:\\study\\NewPeople\\data\\WELL数据看板.html"
shutil.copyfile(html_path, shallow)
print("COPIED ->", shallow)

