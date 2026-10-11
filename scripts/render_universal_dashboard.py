#!/usr/bin/env python3
"""
通用指标看板渲染核心 v3 —— 飞书风格 Stripe 式设计系统
(config v2: components[] + 24 列网格 + 类型注册表；v1 四段是语法糖零改动兼容)
每个组件的视觉层按飞书设计系统精确值构建。
"""
import argparse, json, re, sqlite3, sys, math
from pathlib import Path
from datetime import datetime
import yaml

# ===== 设计 Token（飞书风格） =====
INK = "#1f2329"; INK2 = "#373c43"; SUB = "#646a73"; MUTE = "#8f959e"; FAINT = "#aeb4bd"
BORDER_S = "#dee0e3"; SPLIT = "#eff0f2"; LAYER = "#f2f3f5"
BD = "rgba(16,24,40,.07)"; BD_HOVER = "rgba(16,24,40,.12)"
SURFACE = "#fff"; CANVAS = "#f5f6f7"
BLUE = "#1456f0"; BLUE_H = "#0f48d4"; TEAL = "#00a6a6"; PURPLE = "#722ed1"; AMBER = "#ff7d00"
SERIES = [BLUE, TEAL, PURPLE, AMBER]
OK = "#00b42a"; OK_TXT = "#00875a"; OK_BG = "rgba(0,180,42,.08)"
BAD = "#f53f3f"; BAD_TXT = "#cb2634"; BAD_BG = "rgba(245,63,63,.08)"
AMBER_TXT = "#c26100"; AMBER_BG = "rgba(255,125,0,.1)"
SHADOW = "0 1px 1px rgba(16,24,40,.04), 0 4px 12px rgba(16,24,40,.06), 0 16px 40px -12px rgba(16,24,40,.10)"
SHADOW_H = "0 2px 2px rgba(16,24,40,.05), 0 8px 20px rgba(16,24,40,.09), 0 24px 56px -12px rgba(16,24,40,.16)"
EASE = "cubic-bezier(.4, 0, .2, 1)"
GRID_COLS = 24
FONT = '"Inter","Microsoft YaHei",system-ui,sans-serif'

TYPE_DEFAULTS = {
    # 非对称双栏模式：主图宽(16) 配副图窄(8)，视觉有主次不呆板
    # 自然配对：line(16)+bar(8) / line(16)+pie(8) / funnel(16)+bullet(8) / area_stack(16)+gauge(8)
    # 等宽配对：histogram(12)+scatter(12)
    # 全宽：heatmap(24) / table(24) / heading(24) / text(24)
    "kpi": (6, 5), "line": (16, 6), "bar": (8, 6), "pie": (8, 8),
    "heatmap": (24, 10), "table": (24, 9), "histogram": (12, 6),
    "text": (24, 2), "heading": (24, 1),
    "area_stack": (16, 6), "scatter": (12, 6), "funnel": (16, 6), "bullet": (8, 5),
    "waterfall": (16, 7), "sankey": (16, 8), "radar": (8, 7), "gauge": (8, 5),
    # 统计分析扩展（v4）：箱线图 / 正态QQ / 帕累托 / 缺失值画像 / 相关矩阵 / 回归散点
    "box": (12, 6), "qq": (12, 6), "pareto": (16, 7),
    "missing": (12, 6), "corr": (12, 7), "regress": (12, 6),
}

def _norm_ppf(p):
    """标准正态分位数（Acklam 有理逼近，绝对误差 < 1.15e-9）——正态Q-Q图用，不引入 scipy 依赖。"""
    import math as _m
    if p <= 0.0: return -8.0
    if p >= 1.0: return 8.0
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q_ = (-2 * _m.log(p)) ** 0.5
        return (((((c[0] * q_ + c[1]) * q_ + c[2]) * q_ + c[3]) * q_ + c[4]) * q_ + c[5]) / \
               ((((d[0] * q_ + d[1]) * q_ + d[2]) * q_ + d[3]) * q_ + 1)
    if p > phigh:
        q_ = (-2 * _m.log(1 - p)) ** 0.5
        return -(((((c[0] * q_ + c[1]) * q_ + c[2]) * q_ + c[3]) * q_ + c[4]) * q_ + c[5]) / \
               ((((d[0] * q_ + d[1]) * q_ + d[2]) * q_ + d[3]) * q_ + 1)
    q_ = p - 0.5
    r_ = q_ * q_
    return (((((a[0] * r_ + a[1]) * r_ + a[2]) * r_ + a[3]) * r_ + a[4]) * r_ + a[5]) * q_ / \
           (((((b[0] * r_ + b[1]) * r_ + b[2]) * r_ + b[3]) * r_ + b[4]) * r_ + 1)


def parse_caliber_cards(kal_path):
    cards = []
    if not kal_path.exists(): return cards
    text = kal_path.read_text(encoding="utf-8")
    for m in re.finditer(r"^#{2,3}\s*(?:口径卡\s*)?卡?\s*(?:\d+\s*)?[：:]\s*(.+?)\n(.*?)(?=\n#{2,3}\s|\Z)", text, re.S | re.M):
        name, body = m.group(1).strip(), m.group(2)
        ym = re.search(r"```(?:yaml)?\n(.*?)```", body, re.S)
        fields = {}
        if ym:
            for line in ym.group(1).splitlines():
                fm = re.match(r"^(指标名|分子|分母|分母状态过滤|只算什么|不算什么|豁免规则|更新周期)\s*[：:]\s*(.+)$", line.strip())
                if fm: fields[fm.group(1)] = fm.group(2).strip()
        if fields: cards.append({"name": name, **fields})
    return cards

def match_caliber(cards, *keywords):
    kws = [k for k in keywords if k and len(str(k)) >= 2]
    best, best_score = None, 0
    for card in cards:
        name, body = card["name"], card.get("分子", "") + card.get("分母", "")
        score = sum(3 for k in kws if str(k) in name) + sum(1 for k in kws if str(k) in body)
        if score > best_score: best, best_score = card, score
    return best if best_score > 0 else None

def scaled_pct(colname, values):
    vs = [v for v in values if isinstance(v, (int, float))]
    if not vs or not re.search(r"rate|pct|ratio|share", colname or "", re.I): return False
    return max(vs) <= 1.0001

def q(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params)]

COL_CN = {
    "flight_date":"飞行日期","airport_name":"机场","aircraft_model":"机型","wildlife_species":"物种",
    "damage_level":"损伤等级","is_serious":"严重","cost_total":"维修成本","species_name":"物种",
    "species_cn":"物种(中)","is_bird":"是鸟类","is_identified":"已识别","state_name":"州","state_cn":"州(中)",
    "phase_name":"阶段","phase_cn":"阶段(中)","title":"片名","release_year":"上映年","avg_rating":"平均分",
    "high_rating_rate":"好评率","popularity_rank":"热度排名","good_movie_rank":"好评榜排名",
    "genre_cn":"类型","share_pct":"份额","tag_norm":"标签","tag_cnt":"标签次数","user_cnt":"用户数",
    "movie_cnt":"电影数","usage_rank":"使用排名","repo_name":"仓库","actor_login":"贡献者",
    "star_cnt":"Star 数","fork_cnt":"Fork 数","pr_cnt":"PR 数","pr_merge_rate":"PR 合并率",
    "commit_cnt":"提交数","commit_distinct_cnt":"去重提交","core_evt_cnt":"核心事件",
    "heat_score":"热度分","heat_rank":"热度排名","activity_rank":"活跃排名","is_high_freq":"高频仓库",
    "issue_cnt":"Issue 数","created_at":"时间","evt_type":"事件类型","push_cnt":"推送数",
    "pr_opened_cnt":"发起 PR","pr_merged_cnt":"合并 PR","issue_opened_cnt":"发起 Issue",
    "contributor_rank":"贡献排名","rnk_by_cost":"成本排名","rnk_by_rate":"率排名","rnk_by_cnt":"次数排名",
    "airport_state":"州","is_military":"军用","rating_cnt":"评分条数","rating_value":"星级",
    "pct":"占比","user_id":"用户","movie_id":"电影ID","rating":"评分","actor_id":"贡献者ID",
    "repo_id":"仓库ID","is_push":"推送","repo_active_total":"活跃仓库数","contributor_cnt":"贡献者数",
    "bot_account_cnt":"机器人账号数","pr_cnt_human":"真人PR数","pr_merged_human":"真人合并PR",
    "issue_cnt_human":"真人Issue数","release_cnt":"发版数","evt_total":"事件总数",
}
# 字段中文业务名补录注册表（单一事实源；contracts 闸门从这里导入）
FIELD_CN = {
    # ---- 演示数据集字典 v3 ----
    "值": "数值", "单位": "单位", "指标": "指标", "维度": "维度",
    "销售额合计": "销售额合计", "订单行数": "订单行数", "客户数": "客户数",
    "亏损订单行数": "亏损订单行数", "月度销售额": "月度销售额", "月份": "月份",
    "城市": "城市", "省份": "省份", "产品类别": "产品类别", "客户类型": "客户类型",
    "产品名称": "产品名称", "客户": "客户", "订单号": "订单号", "订单日期": "订单日期",
    "折扣": "折扣", "折扣档": "折扣档位", "销售额": "销售额", "数量": "数量", "利润": "利润",
    "行数": "行数", "总数": "总数", "累计占比": "累计占比",
    # ---- 占位 ----
    # ---- ODF 补充字典 ----
    "EQUIPMENTTYPE": "设备类型", "equipmenttype": "设备类型",
    "total_cnt": "资源总数", "city_cnt": "覆盖地市数",
    "nfcstat": "NFC标签状态", "county_cnt": "覆盖区县数", "has_coord": "含坐标数",

    # ---- 电影库补充字典 ----
    "movieid": "电影ID", "userid": "用户ID", "genre_cn": "类型", "yr2": "年份", "year": "年份",
    "total_films": "电影总数", "rating_cnt": "评分数", "genre_cnt": "类型数",
    "valid_tags": "有效标签数", "no_year": "无年份影片数", "score": "评分",

    # ---- WELL 数据集字段字典 v2（官方中文名来自《4个哑资源视图1204》）----
    "ID": "标识", "NAME": "名称", "CODE": "编码", "NFCID": "NFC标签",
    "LIFECYCLESTATUS": "生命周期状态", "VIRTUALCATEGORY": "显示类别",
    "PROPERTYCATEGORY": "产权性质", "PROVINCE_ID": "所属省", "COUNTY_ID": "所属区县",
    "PREFECTURE_ID": "所属地市", "ONLINEDATE": "入网时间", "LONGITUDE": "经度",
    "LATITUDE": "纬度", "CREATEDATE": "创建时间", "CITY_P": "地市(解析)", "COUNTY_P": "区县(解析)",
    "lifecyclestatus": "生命周期状态", "virtualcategory": "显示类别",
    "propertycategory": "产权性质", "city": "地市(解析)", "county": "区县(解析)",
    "forbidden": "是否标记禁用", "firstwell": "是否局前井",
    "fld": "字段", "val": "码值", "meaning": "含义", "basis": "依据",
    "cnt": "数量", "yr": "入网年份", "total_wells": "管线井总数",
    "zaiwang_cnt": "在网数量", "zaiwang_pct": "在网占比",
    "county_parsed_cnt": "覆盖区县数", "has_location": "含坐标井数", "city_parsed_cnt": "覆盖地市数",

}
def col_cn(c): return FIELD_CN.get(c) or COL_CN.get(c, c)

# ===== 网格引擎 =====
def _overlap(x, y, w, h, p):
    return not (x + w <= p["x"] or p["x"] + p["w"] <= x or y + h <= p["y"] or p["y"] + p["h"] <= y)

def _first_fit(placed, w, h):
    y = 0
    while True:
        for x in range(0, GRID_COLS - w + 1):
            if not any(_overlap(x, y, w, h, p) for p in placed): return x, y
        y += 1

def normalize_components(cfg):
    comps = cfg.get("components")
    if not comps:
        comps = []
        kpi_ids = cfg.get("kpi_band") or [m["id"] for m in cfg.get("metrics", []) if m.get("kpi", True)]
        for mid in kpi_ids: comps.append({"id": f"kpi_{mid}", "type": "kpi", "metric": mid})
        if cfg.get("trend"): comps.append({"id": "trend", "type": "line", "metrics": cfg["trend"]["metrics"]})
        if cfg.get("ranking"): r = dict(cfg["ranking"]); r["id"] = "ranking"; r["type"] = "bar"; comps.append(r)
        if cfg.get("heatmap"): h = dict(cfg["heatmap"]); h["id"] = "heatmap"; h["type"] = "heatmap"; comps.append(h)
    warnings = []
    for i, c in enumerate(comps):
        t = c.get("type")
        if t not in TYPE_DEFAULTS:
            raise ValueError(f"未知组件类型: {t}")
        c["id"] = c.get("id") or f"{t}_{i}"
    # KPI 连续分组：max-remainder 均摊填满 24 列（布局规则清单 R4.2）；超 6 张分行（最小宽 4 列）
    i = 0
    while i < len(comps):
        if comps[i]["type"] == "kpi" and (comps[i].get("grid") or {}).get("x") is None:
            j = i
            while j < len(comps) and comps[j]["type"] == "kpi" and (comps[j].get("grid") or {}).get("x") is None: j += 1
            group = comps[i:j]
            n_total = len(group)
            rows_n = max(1, math.ceil(n_total / 6))
            per = math.ceil(n_total / rows_n)
            for s in range(0, n_total, per):
                rowg = group[s:s+per]
                base, rem = divmod(GRID_COLS, len(rowg))
                for k, c in enumerate(rowg):
                    c.setdefault("grid", {}); c["grid"]["w"] = base + (1 if k < rem else 0)
            i = j
        else: i += 1
    # 逐组件处理
    placed = []
    for c in comps:
        dw, dh = TYPE_DEFAULTS[c["type"]]
        g = c.get("grid") or {}
        w = max(1, min(g.get("w", dw), GRID_COLS))
        h = max(1, g.get("h", dh))
        if c["type"] == "bar" and "h" not in g:
            # 模板网格 44px 行高 + 10px 间距（组件高=54h-10）；TopN 条形按每行~37px+标题内边距~100px 自适应
            h = max(h, math.ceil((c.get("top", 5) * 37 + 100) / 54))
        if c["type"] == "heatmap" and "h" not in g:
            # 热力表按行数自适应：每行 ~38px + 表头/标题/内边距 ~130px，上限 14 格
            h = max(6, min(14, math.ceil((c.get("top", 8) * 38 + 130) / 54)))
        x, y = g.get("x"), g.get("y")
        if x is not None and x + w > GRID_COLS:
            warnings.append(f"组件 {c['id']} 越界"); w = GRID_COLS - x; c["warn"] = "声明的列坐标越界，已自动收窄宽度"
        if x is None or y is None:
            x, y = _first_fit(placed, w, h)
        elif any(_overlap(x, y, w, h, p) for p in placed):
            warnings.append(f"组件 {c['id']} 重叠"); x, y = _first_fit(placed, w, h); c["warn"] = "声明的位置与其他组件重叠，已自动挪位"
        placed.append({"x": x, "y": y, "w": w, "h": h})
        c["grid"] = {"x": x, "y": y, "w": w, "h": h}
    # 行满补位（布局规则清单 R4.2/R4.3）：行内 span 之和 <24 时按比例均摊缺口并重排行内 x；
    # 末行孤卡：宽型组件拉伸全宽，卡片型（kpi/bullet/gauge/radar）保持档位宽
    CARD_LIKE = {"kpi", "bullet", "gauge", "radar"}
    rows = {}
    for c in comps: rows.setdefault(c["grid"]["y"], []).append(c)
    for y, row in rows.items():
        # 行高对齐（治行带空白）：同行卡片统一取最大高——图表类 height:100% 弹性填充，
        # 变高=图变大而非留白；排名/表格 space-evenly/flex 同理
        maxh = max(c["grid"]["h"] for c in row)
        for c in row: c["grid"]["h"] = maxh
        total = sum(c["grid"]["w"] for c in row)
        if total >= GRID_COLS:
            pass
        elif len(row) == 1 and row[0]["type"] in CARD_LIKE:
            pass  # 孤卡保持档位宽（Metabase 同款行为）
        else:
            if len(row) == 1:
                row[0]["grid"]["w"] = GRID_COLS  # 孤张宽型组件拉伸全宽
            else:
                deficit = GRID_COLS - total
                shares = [c["grid"]["w"] / total * deficit for c in row]
                ints = [int(s) for s in shares]
                rem = deficit - sum(ints)
                order = sorted(range(len(row)), key=lambda i: shares[i] - ints[i], reverse=True)
                for i in range(rem): ints[order[i]] += 1
                for c, add in zip(row, ints):
                    c["grid"]["w"] += add
            row.sort(key=lambda c: c["grid"]["x"])
            x = 0
            for c in row:
                c["grid"]["x"] = x; x += c["grid"]["w"]
    # 行满调整后整体重放（防拉伸/加宽致跨行重叠）：按原顺序用新宽度重新 first-fit
    placed = []
    for c in sorted(comps, key=lambda c: (c["grid"]["y"], c["grid"]["x"])):
        w, h = c["grid"]["w"], c["grid"]["h"]
        x, y = _first_fit(placed, w, h)
        placed.append({"x": x, "y": y, "w": w, "h": h})
        c["grid"] = {"x": x, "y": y, "w": w, "h": h}
    return comps, warnings

def normalize_domains(cfg):
    if not cfg.get("domains"):
        comps, warns = normalize_components(cfg)
        return [{"id": "default", "label": "", "components": comps}], warns
    domains, all_warns = [], []
    for di, d in enumerate(cfg["domains"]):
        did = d.get("id") or f"d{di}"
        sub = {"version": 2, "components": d.get("components", [])}
        comps, warns = normalize_components(sub)
        for c in comps: c["id"] = f"{did}_{c['id']}"
        all_warns.extend(warns)
        domains.append({"id": did, "label": d.get("label", ""), "components": comps})
    return domains, all_warns

# ===== 组件数据构建 =====
def build_data(case_dir, cfg):
    conn = sqlite3.connect(f"file:{case_dir/'warehouse.db'}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cards = parse_caliber_cards(case_dir / "artifacts" / "口径卡.md")
    metrics = {m["id"]: m for m in cfg.get("metrics", [])}
    tcfg = cfg.get("time"); times = []
    if tcfg:
        tconds = [f'"{tcfg["column"]}" IS NOT NULL']; tparams = []
        if tcfg.get("from"): tconds.append(f'"{tcfg["column"]}" >= ?'); tparams.append(tcfg["from"])
        if tcfg.get("to"): tconds.append(f'"{tcfg["column"]}" <= ?'); tparams.append(tcfg["to"])
        rows = q(conn, f'SELECT "{tcfg["column"]}" AS t FROM "{tcfg["table"]}" WHERE {" AND ".join(tconds)} ORDER BY 1', tparams)
        times = [r["t"] for r in rows]
    kpi_at = (tcfg or {}).get("kpi_at")

    def series_of(m):
        if not tcfg: return []
        src = m["source"]
        if src.get("table") != tcfg["table"]:
            cols = [c[1] for c in conn.execute(f'PRAGMA table_info("{src["table"]}")')]
            if tcfg["column"] not in cols: return []
        key = src.get("key") or {}
        params = list(key.values())
        conds = [f'"{k}" = ?' for k in key] + [f'"{tcfg["column"]}" IS NOT NULL']
        if tcfg.get("from"): conds.append(f'"{tcfg["column"]}" >= ?'); params.append(tcfg["from"])
        if tcfg.get("to"): conds.append(f'"{tcfg["column"]}" <= ?'); params.append(tcfg["to"])
        return [(r["t"], r["v"]) for r in q(conn,
            f'SELECT "{tcfg["column"]}" AS t, "{src["column"]}" AS v FROM "{src["table"]}" WHERE {" AND ".join(conds)} ORDER BY 1', params)]

    def latest_of(m):
        src = m["source"]; key = src.get("key") or {}
        conds, params = [], list(key.values())
        for k in key: conds.append(f'"{k}" = ?')
        where = " WHERE " + " AND ".join(conds) if conds else ""
        vals = [r["v"] for r in q(conn, f'SELECT "{src["column"]}" AS v FROM "{src["table"]}"{where}', params) if r["v"] is not None]
        return vals[-1] if vals else None

    def kpi_payload(mid):
        m = metrics.get(mid)
        if not m: return None
        hist = series_of(m)
        if kpi_at is not None and hist:
            hmap = dict(hist); val = hmap.get(kpi_at, hist[-1][1])
            idx = [i for i,(tt,_) in enumerate(hist) if tt == kpi_at]
            prev = hist[idx[0]-1][1] if idx and idx[0] > 0 else None
        else:
            val = hist[-1][1] if hist else latest_of(m); prev = hist[-2][1] if len(hist) >= 2 else None
        if scaled_pct(m["source"]["column"], [v for v in (val,prev) if v is not None] + [v for _,v in hist]):
            if isinstance(val,(int,float)): val = round(val*100,4)
            if isinstance(prev,(int,float)): prev = round(prev*100,4)
            hist = [(t, round(v*100,4) if isinstance(v,(int,float)) else v) for t,v in hist]
        delta_pct, good = None, None
        if prev not in (None,0) and val is not None and isinstance(val,(int,float)):
            delta_pct = (val - prev) / abs(prev) * 100
            good = (delta_pct >= 0) == (m.get("direction","up") == "up")
        cal = match_caliber(cards, m.get("caliber",""), m["name"], mid)
        return {"id":mid,"name":m["name"],"unit":m.get("unit",""),"direction":m.get("direction","up"),
                "value":val,"delta_pct":round(delta_pct,1) if delta_pct is not None else None,
                "good":good,"spark":[v for _,v in hist][-24:],"caliber":cal}

    warnings = []
    domains, norm_warn = normalize_domains(cfg)
    warnings.extend(norm_warn)
    kpisById = {}

    def table_cols(t): return [c[1] for c in conn.execute(f'PRAGMA table_info("{t}")')]

    def _agg_table(comp, m):
        """解析聚合值列（v4 加固）。

        修正的历史缺陷：旧逻辑在「组件自带聚合表」时把 metric 的**ID** 当列名用，
        于是 metric="sales" + table="ads_province" 会静默生成 vcol="sales"，
        取到的全是字符串，累计占比/数值全为 0（图表看起来正常但完全错误）。
        现按 显式 value_col -> 指标源列 -> 指标ID -> 指标名 依次探测真实列名。
        """
        cols = table_cols(comp["table"])
        cands = []
        if comp.get("value_col"): cands.append(comp["value_col"])
        if m and (m.get("source") or {}).get("column"):
            src = m["source"]
            # 指标源就是本表时最可信；源在别的表时仅作为候选
            if src.get("table") == comp["table"]: cands.insert(0, src["column"])
            else: cands.append(src["column"])
        if comp.get("metric"): cands.append(comp["metric"])
        if m and m.get("name"): cands.append(m["name"])
        vcol = next((c for c in cands if c in cols), None)
        if vcol is None:
            vcol = next((c for c in cols if c not in ("dim", "维度")), comp.get("metric"))
        filt = f' AND ({comp["filter"]})' if comp.get("filter") else ""
        order = f' ORDER BY {comp["order"]}' if comp.get("order") else " ORDER BY v DESC"
        return vcol, filt, order

    def build_comp(c):
        t = c["type"]; d = c
        if t == "kpi":
            return kpi_payload(d.get("metric"))
        if t == "line":
            m0 = metrics.get(d["metrics"][0]) if d["metrics"] else None
            series = []
            for mid in d["metrics"]:
                m = metrics.get(mid)
                if not m: continue
                pairs = series_of(m)
                if scaled_pct(m["source"]["column"], [v for _,v in pairs]):
                    pairs = [(tt, round(v*100,4) if isinstance(v,(int,float)) else v) for tt,v in pairs]
                hist = dict(pairs)
                series.append({"id":mid,"name":m["name"],"data":[hist.get(tt) for tt in times]})
            return {"times":times,"series":series,"caliber":match_caliber(cards,m0.get("caliber","") if m0 else "",m0["name"] if m0 else "") if m0 else None}
        if t == "bar":
            m = metrics.get(d.get("metric"))
            vcol, filt, order = _agg_table(d, m)
            rows = q(conn, f'SELECT "{d["dimension"]}" AS dm, "{vcol}" AS v FROM "{d["table"]}" WHERE "{d["dimension"]}" IS NOT NULL{filt}{order} LIMIT {d.get("top",5)}')
            vals = [r["v"] for r in rows]
            if scaled_pct(vcol, vals): rows = [{"dm":r["dm"],"v":round(r["v"]*100,2)} for r in rows]
            return {"title":d.get("label") or f'{m["name"] if m else ""} · Top{d.get("top",5)}',
                    "unit":m.get("unit","") if m else "","dimension":d.get("dimension"),
                    "direction":m.get("direction","up") if m else "up",
                    "rows":[{"label":str(r["dm"]),"value":r["v"]} for r in rows]}
        if t == "pie":
            m = metrics.get(d.get("metric"))
            vcol, filt, order = _agg_table(d, m)
            rows = q(conn, f'SELECT "{d["dimension"]}" AS dm, "{vcol}" AS v FROM "{d["table"]}" '
                          f'WHERE "{d["dimension"]}" IS NOT NULL{filt}{order} LIMIT {d.get("top",8)}')
            vals = [r["v"] for r in rows]
            if scaled_pct(vcol, vals): rows = [{"dm":r["dm"],"v":round(r["v"]*100,2)} for r in rows]
            slices = [{"label":str(r["dm"]),"value":r["v"]} for r in rows if r["v"] is not None]
            if len(slices) > 5:
                rest = sum(s["value"] for s in slices[5:] if isinstance(s["value"],(int,float)))
                slices = slices[:5] + [{"label":"其他","value":rest or 0}]
                warnings.append(f"饼图 {c['id']} 超5块已自动合并'其他'（规则#1）")
                c["warn"] = "构成超 5 块，已自动保留前 5 块、其余合并为\"其他\"（规则#1）"
            return {"title":d.get("label") or f'{m["name"] if m else ""} 构成',
                    "unit":m.get("unit","") if m else "",
                    "total":sum(s["value"] for s in slices if isinstance(s["value"],(int,float))),"slices":slices}
        if t == "heatmap":
            hmetrics = []
            for entry in d.get("metrics", []):
                mid, col = (entry["metric"], entry["column"]) if isinstance(entry, dict) else (entry, None)
                m = metrics.get(mid)
                if m: hmetrics.append({"id":mid,"name":m["name"],"unit":m.get("unit",""),
                                       "direction":m.get("direction","up"),"column":col})
            where = f' WHERE {d["filter"]}' if d.get("filter") else ""
            order = f' ORDER BY {d["order"]}' if d.get("order") else ""
            rows = q(conn, f'SELECT * FROM "{d["table"]}"{where}{order} LIMIT {d.get("top",12)*4}')
            seen, hm_rows = set(), []
            for r in rows:
                dv = r[d["dimension"]]
                if dv is None or dv in seen: continue
                seen.add(dv); cells = {}
                for hm in hmetrics:
                    col = hm.get("column") or metrics[hm["id"]]["source"]["column"]
                    cells[hm["id"]] = r.get(col)
                hm_rows.append({"label":str(dv),"cells":cells})
                if len(hm_rows) >= d.get("top",12): break
            for hm in hmetrics:
                col = hm.get("column") or metrics[hm["id"]]["source"]["column"]
                if scaled_pct(col, [r["cells"].get(hm["id"]) for r in hm_rows]):
                    for r in hm_rows:
                        v = r["cells"].get(hm["id"])
                        if isinstance(v,(int,float)): r["cells"][hm["id"]] = round(v*100,4)
            return {"dimension_label":d.get("dimension_label",d["dimension"]),"cols":hmetrics,"rows":hm_rows}
        if t == "table":
            tcols = d.get("columns") or table_cols(d["table"])
            where = f' WHERE {d["filter"]}' if d.get("filter") else ""
            order = f' ORDER BY {d["order"]}' if d.get("order") else ""
            rows = q(conn, f'SELECT {", ".join(chr(34)+x+chr(34) for x in tcols)} FROM "{d["table"]}"{where}{order} LIMIT {d.get("top",15)}')
            pct_cols = {x for x in tcols if scaled_pct(x, [r.get(x) for r in rows])}
            if pct_cols:
                for r in rows:
                    for x in pct_cols:
                        if isinstance(r.get(x),(int,float)): r[x] = round(r[x]*100,4)
            return {"cols":[{"key":x,"name":col_cn(x)+("(%)" if x in pct_cols else "")} for x in tcols],
                    "rows":rows,"dimension":d.get("dimension")}
        if t == "histogram":
            col = d["column"]
            if d.get("count_col"):
                rows = q(conn, f'SELECT "{col}" AS b, "{d["count_col"]}" AS c FROM "{d["table"]}" WHERE "{col}" IS NOT NULL ORDER BY 1')
                return {"bins":[str(r["b"]) for r in rows],"counts":[r["c"] for r in rows],"x_label":d.get("label") or col_cn(col)}
            nbins = d.get("bins",10)
            rows = q(conn, f'SELECT "{col}" AS v FROM "{d["table"]}" WHERE "{col}" IS NOT NULL LIMIT 200000')
            vs = sorted(float(r["v"]) for r in rows)
            if not vs: return {"bins":[],"counts":[],"x_label":col_cn(col)}
            lo, hi = vs[0], vs[-1]; rng = (hi-lo) or 1
            counts = [0]*nbins
            for v in vs: counts[min(int((v-lo)/rng*nbins),nbins-1)] += 1
            bins = [f"{lo+rng*i/nbins:.4g}~{lo+rng*(i+1)/nbins:.4g}" if nbins<=12 else f"{lo+rng*i/nbins:.3g}" for i in range(nbins)]
            return {"bins":bins,"counts":counts,"x_label":d.get("label") or col_cn(col)}
        if t == "text": return {"content":d.get("content","")}
        if t == "heading": return {"content":d.get("content","")}
        # ---------- 统计分析扩展（v4）：箱线图 / 正态QQ / 帕累托 / 缺失值 / 相关矩阵 / 回归 ----------
        # ---------- 统计分析扩展（v4）：箱线图 / 正态QQ / 帕累托 / 缺失值 / 相关矩阵 / 回归 ----------
        if t == "box":
            import statistics as _st
            dim, vcol, filt = d["dimension"], d["column"], (f' WHERE {d["filter"]}' if d.get("filter") else "")
            rows = q(conn, f'SELECT "{dim}" AS dm, "{vcol}" AS v FROM "{d["table"]}" '
                           f'WHERE "{dim}" IS NOT NULL AND "{vcol}" IS NOT NULL{filt}')
            buckets = {}
            for r in rows:
                try: buckets.setdefault(str(r["dm"]), []).append(float(r["v"]))
                except (TypeError, ValueError): pass
            groups, outliers_out = [], []
            for name, vals in buckets.items():
                if len(vals) < 2: continue
                vals.sort(); n = len(vals)
                def _q(p):
                    pos = (n - 1) * p; lo = int(pos); hi = min(lo + 1, n - 1); frac = pos - lo
                    return vals[lo] * (1 - frac) + vals[hi] * frac
                q1, med, q3 = _q(.25), _q(.5), _q(.75); iqr = q3 - q1
                lo_f, hi_f = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                inside = [v for v in vals if lo_f <= v <= hi_f]
                outs = [v for v in vals if v < lo_f or v > hi_f]
                mean = sum(vals) / n
                groups.append({"name": name, "min": round(min(inside), 6), "q1": round(q1, 6),
                               "median": round(med, 6), "q3": round(q3, 6), "max": round(max(inside), 6),
                               "n": n, "outliers": len(outs),
                               "mean": round(mean, 6), "std": round(_st.pstdev(vals), 6),
                               "cv": round(_st.pstdev(vals) / mean, 4) if mean else None})
                outliers_out += [{"g": name, "v": round(v, 6)} for v in outs[:40]]
            groups.sort(key=lambda g: -g["median"])
            groups = groups[:d.get("top", 10)]
            keep = {g["name"] for g in groups}
            return {"groups": groups, "outliers_pts": [o for o in outliers_out if o["g"] in keep][:300],
                    "y_label": col_cn(vcol), "x_label": col_cn(dim),
                    "outlier_total": sum(g["outliers"] for g in groups)}
        if t == "qq":
            import statistics as _st
            vcol = d["column"]; filt = f' WHERE {d["filter"]}' if d.get("filter") else ""
            vals = []
            for r in q(conn, f'SELECT "{vcol}" AS v FROM "{d["table"]}" WHERE "{vcol}" IS NOT NULL{filt}'):
                try: vals.append(float(r["v"]))
                except (TypeError, ValueError): pass
            if len(vals) < 8:
                return {"points": [], "ref": [], "n": len(vals), "note": "样本量不足以做正态Q-Q（需 >= 8）"}
            vals.sort(); n = len(vals); mu = sum(vals) / n; sd = _st.pstdev(vals)
            pts = []
            for i, v in enumerate(vals, start=1):
                p = (i - 0.375) / (n + 0.25)
                pts.append([round(_norm_ppf(p), 5), round(v, 6)])
            zs = [p[0] for p in pts]
            zmin, zmax = min(zs), max(zs)
            slope = sd if sd else 1
            ref = [[round(zmin, 5), round(mu + slope * zmin, 6)], [round(zmax, 5), round(mu + slope * zmax, 6)]]
            skew = round(sum(((v - mu) / sd) ** 3 for v in vals) / n, 4) if sd else None
            kurt = round(sum(((v - mu) / sd) ** 4 for v in vals) / n - 3, 4) if sd else None
            return {"points": pts[:d.get("top", 2000)], "ref": ref, "n": n,
                    "mean": round(mu, 6), "std": round(sd, 6), "skew": skew, "kurtosis": kurt,
                    "x_label": "理论分位数", "y_label": col_cn(vcol),
                    "note": "样本量 > 5000，参考偏度/峰度判断" if n > 5000 else ""}
        if t == "pareto":
            m = metrics.get(d.get("metric"))
            vcol, _filt, order = _agg_table(d, m)
            rows = q(conn, f'SELECT "{d["dimension"]}" AS dm, "{vcol}" AS v FROM "{d["table"]}" '
                          f'WHERE "{d["dimension"]}" IS NOT NULL{order} LIMIT {d.get("top", 12)}')
            labels = [str(r["dm"]) for r in rows]
            values = [r["v"] or 0 for r in rows]
            total = sum(v for v in values if isinstance(v, (int, float)))
            cum, run = [], 0.0
            for v in values:
                run += v if isinstance(v, (int, float)) else 0
                cum.append(round(run / total * 100, 2) if total else 0)
            vital_idx = next((i for i, cv in enumerate(cum) if cv >= 80), None)
            return {"title": d.get("label") or f'{(m or {}).get("name", "")} 帕累托分析',
                    "unit": (m or {}).get("unit", ""), "labels": labels,
                    "values": values, "cum": cum, "total": total,
                    "vital_label": (labels[vital_idx] if vital_idx is not None else None),
                    "vital_count": (vital_idx + 1 if vital_idx is not None else None)}
        if t == "missing":
            rows = q(conn, f'SELECT * FROM "{d["table"]}"')
            if not rows:
                return {"labels": [], "overall": [], "counts": [], "group_col": None}
            gcol = d.get("dimension")
            groups = {}
            for r in rows:
                key = str(r.get(gcol)) if gcol else "全部"
                groups.setdefault(key, []).append(r)
            labels, rate, cnt = [], [], []
            for key, rs in groups.items():
                nn = len(rs); cells = nn * len(rs[0]); miss = 0
                for r in rs:
                    for v in r.values():
                        if v is None or (isinstance(v, str) and v.strip() == ""): miss += 1
                labels.append(key); cnt.append(nn)
                rate.append(round(miss / cells * 100, 2) if cells else 0.0)
            order = sorted(range(len(labels)), key=lambda i: -rate[i])[:d.get("top", 12)]
            overall = []
            for col in rows[0].keys():
                nm = sum(1 for r in rows
                         if r.get(col) is None or (isinstance(r.get(col), str) and str(r.get(col)).strip() == ""))
                overall.append({"col": col_cn(col), "key": col, "rate": round(nm / len(rows) * 100, 2), "n": nm})
            overall.sort(key=lambda x: -x["rate"])
            return {"labels": [labels[i] for i in order], "rates": [rate[i] for i in order],
                    "counts": [cnt[i] for i in order],
                    "overall": overall[:d.get("col_top", 15)],
                    "group_col": col_cn(gcol) if gcol else None}
        if t == "corr":
            cols = d.get("columns") or []
            rows = q(conn, f'SELECT {", ".join(chr(34)+x+chr(34) for x in cols)} FROM "{d["table"]}"')
            pairs = []
            for r in rows:
                vals, ok = [], True
                for x in cols:
                    try: vals.append(float(r[x]))
                    except (TypeError, ValueError): ok = False; break
                if ok: pairs.append(vals)
            method = (d.get("method") or "pearson").lower()
            def _rank(seq):
                idx = sorted(range(len(seq)), key=lambda i: seq[i]); rk = [0.0] * len(seq); i = 0
                while i < len(idx):
                    j = i
                    while j + 1 < len(idx) and seq[idx[j + 1]] == seq[idx[i]]: j += 1
                    avg = (i + j) / 2 + 1
                    for k in range(i, j + 1): rk[idx[k]] = avg
                    i = j + 1
                return rk
            def _pearson(a, b):
                n = len(a)
                if n < 3: return None
                ma_, mb_ = sum(a) / n, sum(b) / n
                num = sum((a[i] - ma_) * (b[i] - mb_) for i in range(n))
                da = sum((x - ma_) ** 2 for x in a) ** 0.5
                db = sum((x - mb_) ** 2 for x in b) ** 0.5
                return round(num / (da * db), 4) if da and db else None
            series = list(zip(*pairs)) if pairs else [[] for _ in cols]
            if method == "spearman":
                series = [_rank(list(x)) for x in series]
            matrix, labels = [], [col_cn(c) for c in cols]
            for i in range(len(cols)):
                matrix.append([1.0 if i == j else _pearson(list(series[i]), list(series[j])) for j in range(len(cols))])
            flat = [abs(v) for row in matrix for v in row if isinstance(v, (int, float)) and v != 1.0]
            return {"labels": labels, "keys": cols, "matrix": matrix, "method": method,
                    "n": len(pairs), "max_abs": round(max(flat), 4) if flat else None,
                    "title": d.get("label") or f"{'斯皮尔曼' if method == 'spearman' else '皮尔逊'}相关矩阵"}
        if t == "regress":
            xcol, ycol = d["x"], d["y"]
            filt = f' WHERE {d["filter"]}' if d.get("filter") else ""
            rows = q(conn, f'SELECT "{xcol}" AS x, "{ycol}" AS y FROM "{d["table"]}" '
                          f'WHERE "{xcol}" IS NOT NULL AND "{ycol}" IS NOT NULL{filt} LIMIT {d.get("top", 2000)}')
            pts = []
            for r in rows:
                try: pts.append([float(r["x"]), float(r["y"])])
                except (TypeError, ValueError): pass
            if len(pts) < 3:
                return {"points": pts, "n": len(pts), "note": "样本量不足以拟合（需 >= 3）"}
            n = len(pts); sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
            sxx = sum(p[0] ** 2 for p in pts); sxy = sum(p[0] * p[1] for p in pts)
            den = n * sxx - sx * sx
            slope = (n * sxy - sx * sy) / den if den else 0.0
            intercept = (sy - slope * sx) / n
            my = sy / n
            ss_tot = sum((p[1] - my) ** 2 for p in pts)
            ss_res = sum((p[1] - (intercept + slope * p[0])) ** 2 for p in pts)
            r2 = round(1 - ss_res / ss_tot, 4) if ss_tot else None
            r = round((1 - ss_res / ss_tot) ** 0.5, 4) if ss_tot and ss_res <= ss_tot else None
            xmin = min(p[0] for p in pts); xmax = max(p[0] for p in pts)
            return {"points": pts, "n": n, "r2": r2, "r": r,
                    "slope": round(slope, 6), "intercept": round(intercept, 6),
                    "fit": [[round(xmin, 6), round(intercept + slope * xmin, 6)],
                            [round(xmax, 6), round(intercept + slope * xmax, 6)]],
                    "x_label": col_cn(xcol), "y_label": col_cn(ycol),
                    "title": d.get("label") or f"{col_cn(ycol)} 与 {col_cn(xcol)} 回归"}

        if t == "area_stack":
            tcol = d.get("time_col") or (tcfg or {}).get("column")
            filt = f' AND ({d["filter"]})' if d.get("filter") else ""
            rows = q(conn, f'SELECT "{d["dimension"]}" AS dim, "{tcol}" AS t, "{d["metric"]}" AS v '
                          f'FROM "{d["table"]}" WHERE "{d["dimension"]}" IS NOT NULL AND "{tcol}" IS NOT NULL{filt}')
            agg = {}
            for r in rows: agg.setdefault(str(r["dim"]),{})[r["t"]] = r["v"]
            items = sorted(agg.items(), key=lambda kv: -sum(v for v in kv[1].values() if isinstance(v,(int,float))))[:d.get("top",5)]
            tvals = sorted({r["t"] for r in rows})
            return {"times":tvals,"series":[{"name":k,"data":[vv.get(t) for t in tvals]} for k,vv in items]}
        if t == "scatter":
            filt = f' AND ({d["filter"]})' if d.get("filter") else ""
            # 确定性抽样（Knuth 乘法散列）：分布随机但每次生成一致（验收标准6）
            rows = q(conn, f'SELECT "{d["x"]}" AS x, "{d["y"]}" AS y FROM "{d["table"]}" '
                          f'WHERE "{d["x"]}" IS NOT NULL AND "{d["y"]}" IS NOT NULL{filt} '
                          f'ORDER BY ("{d["x"]}" * 2654435761) % 2147483647 LIMIT {d.get("top",300)}')
            return {"points":[[r["x"],r["y"]] for r in rows],
                    "x_label":d.get("x_label") or col_cn(d["x"]),"y_label":d.get("y_label") or col_cn(d["y"])}
        if t == "funnel":
            stages = []
            for s in d.get("stages", []):
                m = metrics.get(s.get("metric"))
                v = latest_of(m) if m else s.get("value")
                if scaled_pct(m["source"]["column"] if m else "", [v] if v is not None else []):
                    v = round(v*100,2) if isinstance(v,(int,float)) else v
                stages.append({"label":s.get("label",s.get("metric","")),"value":v})
            return {"stages":stages}
        if t == "waterfall":
            return {"items": d.get("items", []), "unit": d.get("unit", "")}
        if t == "sankey":
            pal = ["#3370F4", "#2DBEAB", "#8D55ED", "#FF811A"]
            nodes, c1 = [], 0
            for n in d.get("nodes", []):
                col = n.get("col", 1)
                color = n.get("color") or ("#8F959E" if col == 2 else ("#F54A45" if n.get("bad") else (pal[c1 % 4] if col == 1 else "#35BD4B")))
                if col == 1: c1 += 1
                nodes.append({"name": n["name"], "itemStyle": {"color": color}})
            return {"nodes": nodes, "links": d.get("links", [])}
        if t == "radar":
            rows = q(conn, f'SELECT * FROM "{d["table"]}"')
            cols = []
            for mid in d.get("metrics", []):
                m = metrics.get(mid) or {}
                cols.append((mid, m.get("name", mid), (m.get("source") or {}).get("column", mid)))
            scaled = {}
            for _, _, col in cols:
                vs = [r.get(col) for r in rows if isinstance(r.get(col), (int, float))]
                scaled[col] = bool(vs) and scaled_pct(col, vs)
            def rv(r, col):
                v = r.get(col)
                return round(v * 100, 4) if scaled.get(col) and isinstance(v, (int, float)) else v
            inds = []
            for mid, name, col in cols:
                vs = [rv(r, col) for r in rows]
                vs = [v for v in vs if isinstance(v, (int, float))]
                m = metrics.get(mid) or {}
                inds.append({"name": name + (f"({m.get('unit')})" if m.get("unit") else ""),
                            "max": round(max(vs), 4) if vs else 1})
            oc = cols[0][2]
            tops = sorted([r for r in rows if isinstance(rv(r, oc), (int, float))], key=lambda r: -rv(r, oc))[:d.get("top", 3)]
            return {"indicators": inds,
                    "series": [{"name": str(r[d["dimension"]]), "values": [rv(r, c) for _, _, c in cols]} for r in tops]}
        if t == "gauge":
            p = kpi_payload(d.get("metric")) or {}
            m = metrics.get(d.get("metric")) or {}
            return {"name": m.get("name", d.get("metric")), "value": p.get("value"),
                    "unit": m.get("unit", ""), "max": d.get("max", 100), "caliber": p.get("caliber")}
        if t == "bullet":
            m = metrics.get(d.get("metric"))
            p = kpi_payload(d.get("metric")) or {}
            return {"name":m["name"] if m else d.get("metric"),"unit":m.get("unit","") if m else "",
                    "value":p.get("value"),"target":d.get("target"),
                    "direction":m.get("direction","up") if m else "up","caliber":p.get("caliber")}
        return {"content":f"未知组件类型 {t}"}

    # 逐域逐组件构建
    for dom in domains:
        dom_components = []
        for c in dom["components"]:
            data = build_comp(c)
            if data is None:
                warnings.append(f"组件 {c['id']} 无数据，已跳过"); continue
            # M3 空数据自动隐藏（Metabase hide-empty-cards）：隐藏后行满自动补位
            t = c["type"]
            empty = (t in ("bar","pie") and not data.get("rows") and not data.get("slices")) or                     (t == "table" and not data.get("rows")) or                     (t == "heatmap" and not data.get("rows")) or                     (t == "scatter" and not data.get("points")) or                     (t == "histogram" and not data.get("counts")) or                     (t in ("line","area_stack") and not data.get("series")) or                     (t == "radar" and not data.get("series")) or                     (t == "funnel" and not data.get("stages")) or                     (t == "box" and not data.get("groups")) or                     (t == "qq" and not data.get("points")) or                     (t == "pareto" and not data.get("values")) or                     (t == "missing" and not data.get("overall")) or                     (t == "corr" and not data.get("matrix")) or                     (t == "regress" and not data.get("points"))
            if empty:
                warnings.append(f"组件 {c['id']} 数据为空，已自动隐藏（Metabase M3）"); continue
            comp_out = {"id":c["id"],"type":c["type"],"title":c.get("title",""),
                        "grid":c["grid"],"data":data}
            if c.get("warn"): comp_out["warn"] = c["warn"]
            dom_components.append(comp_out)
        dom["components"] = dom_components
    # drill 数据
    dcfg = cfg.get("drill",{}).get("l2",{})
    l2slices = []
    for s in dcfg.get("slices", []):
        src = s.get("source",{})
        try:
            key = src.get("key") or {}
            conds, params = [], list(key.values())
            for k in key: conds.append(f'"{k}" = ?')
            if src.get("filter"): conds.append(src["filter"])
            where = " WHERE " + " AND ".join(conds) if conds else ""
            agg = (src.get("agg") or "latest").lower()
            if agg == "sum": v = conn.execute(f'SELECT SUM("{src["column"]}") FROM "{src["table"]}"{where}',params).fetchone()[0]
            elif agg == "max": v = conn.execute(f'SELECT MAX("{src["column"]}") FROM "{src["table"]}"{where}',params).fetchone()[0]
            else:
                vs = [r["v"] for r in q(conn,f'SELECT "{src["column"]}" AS v FROM "{src["table"]}"{where}',params) if r["v"] is not None]
                v = vs[-1] if vs else None
            if scaled_pct(src["column"],[v] if v is not None else []):
                v = round(v*100,4) if isinstance(v,(int,float)) else v
            l2slices.append({"label":s.get("label",""),"color":s.get("color","blue"),"value":v,"unit":s.get("unit","")})
        except: l2slices.append({"label":s.get("label",""),"color":"gray","value":None,"unit":""})
    l2dims = []
    for dd in dcfg.get("dimensions", []):
        where = f' WHERE {dd["filter"]}' if dd.get("filter") else ""
        order = f' ORDER BY {dd["order"]}' if dd.get("order") else ""
        rows = q(conn, f'SELECT * FROM "{dd["table"]}"{where}{order} LIMIT 15')
        tc = table_cols(dd["table"])
        pct_cols = {c for c in tc if scaled_pct(c,[r.get(c) for r in rows])}
        if pct_cols:
            for r in rows:
                for x in pct_cols:
                    if isinstance(r.get(x),(int,float)): r[x] = round(r[x]*100,4)
        seen, cols = set(), []
        for c in tc:
            nm = col_cn(c) + ("(%)" if c in pct_cols else "")
            if nm in seen: nm = c  # 翻译重名（如 movie_id/title 都译"电影"）时退回原始列名
            seen.add(nm); cols.append({"key": c, "name": nm})
        l2dims.append({"label":dd.get("label",dd["dimension"]),"dimension":dd["dimension"],
                       "cols":cols,"rows":[dict(r) for r in rows]})
    l3 = None
    l3cfg = cfg.get("drill",{}).get("l3")
    if l3cfg:
        order = f' ORDER BY "{l3cfg["time_col"]}" DESC' if l3cfg.get("time_col") else ""
        total = conn.execute(f'SELECT COUNT(*) FROM "{l3cfg["table"]}"').fetchone()[0]
        rows = q(conn, f'SELECT {", ".join(chr(34)+x+chr(34) for x in l3cfg["columns"])} FROM "{l3cfg["table"]}"{order} LIMIT {l3cfg.get("limit",1000)}')
        fgroups = []
        for f in l3cfg.get("filters", []):
            vals = [str(r[f["column"]]) for r in rows if r.get(f["column"]) is not None]
            fgroups.append({"column":f["column"],"label":f.get("label",col_cn(f["column"])),
                           "values":list(dict.fromkeys(vals))[:10]})
        l3 = {"cols":[{"key":x,"name":col_cn(x)} for x in l3cfg["columns"]],
              "rows":[dict(r) for r in rows],"limit":l3cfg.get("limit",1000),
              "total":total,"truncated":total>l3cfg.get("limit",1000),
              "dim_map":l3cfg.get("dimension_map",{}),"fgroups":fgroups,
              "status":l3cfg.get("status")}
    conn.close()
    return {"title":cfg.get("title",case_dir.name),"generated":datetime.now().strftime("%Y-%m-%d %H:%M"),
            "warnings":warnings,"domains":domains,"kpisById":kpisById,
            "drill":{"l2slices":l2slices,"l2dims":l2dims,"l3":l3}}

# ===== HTML 模板（静态 + DATA 注入） =====

def main():
    import argparse
    ap = argparse.ArgumentParser(description='通用指标看板渲染核心 v3')
    ap.add_argument('case_dir')
    ap.add_argument('--config', default='dashboard.config.yaml')
    ap.add_argument('--output', default=None)
    args = ap.parse_args()
    case_dir = Path(args.case_dir)
    cfg_path = case_dir / args.config
    if not cfg_path.exists():
        for alt in ('dashboard.config.yml', 'dashboard.config.json'):
            if (case_dir / alt).exists():
                cfg_path = case_dir / alt
                break
        else:
            print(f'错误：找不到 {cfg_path}', file=sys.stderr)
            sys.exit(1)
    cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8'))
    # 生成闸门（能力内核②）：渲染前过契约校验——字段存在/中文映射/布局行满/组件类型=硬阻断（退出码 2），
    # 选型不当=警告放行。开销红线：调用方（DSH agent）最多 1 次生成 + 2 轮自纠，超限降级模板。
    try:
        from dashboard_contracts import validate_config
        findings, _ = validate_config(cfg, case_dir)
        errors = [f for f in findings if f["level"] == "error"]
        for f in errors:
            print(f"❌ [闸门打回] {f['loc']}: {f['msg']}", file=sys.stderr)
        for f in findings:
            if f["level"] != "error":
                print(f"⚠️  [闸门警告] {f['loc']}: {f['msg']}")
        if errors:
            print(f"闸门拒绝渲染：{len(errors)} 项硬错误。请修正 config 后重试（最多 2 轮自纠）。", file=sys.stderr)
            sys.exit(2)
    except ImportError:
        pass  # dashboard_contracts 不在同目录时跳过（独立部署兼容）
    data = build_data(case_dir, cfg)
    tmpl_path = Path(__file__).parent / '_dashboard_template.html'
    html_tmpl = tmpl_path.read_text(encoding='utf-8')
    ep = Path(__file__).parent / 'vendor' / 'echarts.min.js'
    ej = ep.read_text(encoding='utf-8') if ep.exists() else ''
    data_js = json.dumps(data, ensure_ascii=False, default=str).replace('</', '<\\/')
    html = (html_tmpl.replace('__DATA__', data_js)
        .replace('__TITLE__', str(data['title']))
        .replace('__GENERATED__', data['generated'])
        .replace('__ECHARTS__', ej))
    out = Path(args.output) if args.output else case_dir / 'dashboard.html'
    out.write_text(html, encoding='utf-8')
    nc = sum(len(dom['components']) for dom in data['domains'])
    nd = len(data['domains'])
    di = f'{nd} 域 ' if nd > 1 else ''
    print(f'✅ 通用看板 v3 已生成：{out}（{di}{nc} 组件 / 警告 {len(data["warnings"])} 条 / {out.stat().st_size/1e6:.1f}MB）')

if __name__ == '__main__':
    main()
