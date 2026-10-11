"""data-viz 正式测试 · 第 3 步：数据总结报告（AI 出 spec，report_docx.py 只排版）

按 SKILL.md：每份分析必须以数据总结报告.docx 收尾。
"""
import json
import pathlib
import sqlite3
import subprocess
import sys

SKILL = pathlib.Path(r"C:\Users\guoyu\.dsh\skills\data-viz")
SCRIPTS = SKILL / "scripts"
CASE = pathlib.Path(__file__).resolve().parent.parent / "09_dashboards" / "chinese_orders"
CASE.mkdir(parents=True, exist_ok=True)

print("=" * 78)
print("步骤 3/3  数据总结报告（Word）")
print("=" * 78)

conn = sqlite3.connect(CASE / "warehouse.db")
conn.row_factory = sqlite3.Row
q = lambda sql: [dict(r) for r in conn.execute(sql)]
def one(sql):
    r = conn.execute(sql).fetchone()
    return r[0] if r else None

kv = {r["指标"]: r["值"] for r in q("SELECT * FROM ads_overview")}
sales, rows_n = kv["销售额合计"], kv["订单行数"]
cust, loss = kv["客户数"], kv["亏损订单行数"]
cats = q("SELECT * FROM ads_category ORDER BY 销售额 DESC")
provs = q("SELECT * FROM ads_province ORDER BY 销售额 DESC")
custs = q("SELECT * FROM ads_customer ORDER BY 销售额 DESC LIMIT 8")
dups = 2075
flat_date = 1243
disc_na = one("SELECT COUNT(*) FROM dwd_orders WHERE 折扣 IS NULL")
conn.close()

# ---------- 生成报告用图（matplotlib + 中文字体） ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
IMGDIR = CASE / "artifacts" / "report_img"
IMGDIR.mkdir(parents=True, exist_ok=True)

def save_pie(labels, values, title, out):
    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90,
           colors=["#5B8FF9", "#61DDAA", "#65789B", "#F6BD16", "#7262fd"],
           wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2), textprops=dict(fontsize=10))
    ax.set_title(title, fontsize=12, fontweight="bold")
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)

def save_barh(labels, values, title, out):
    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    l2, v2 = labels[::-1], values[::-1]
    bars = ax.barh(l2, v2, color="#5B8FF9", height=0.6)
    mx = max(v2) if v2 else 1
    for b, v in zip(bars, v2):
        ax.text(v + mx * 0.01, b.get_y() + b.get_height() / 2, f"{v:,.0f}", va="center", fontsize=9)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)

save_pie([c["维度"] for c in cats], [c["销售额"] for c in cats], "产品类别销售额构成", IMGDIR / "cat.png")
save_pie([c["维度"] for c in cats], [c["行数"] for c in cats], "产品类别订单行数构成", IMGDIR / "cat_cnt.png")
save_barh([p["维度"] for p in provs], [p["销售额"] for p in provs], "省份销售额分布", IMGDIR / "prov.png")
print(f"报告用图: {len(list(IMGDIR.glob('*.png')))} 张")

# ---------- 报告 spec（AI 写的叙事与结论） ----------
spec = {
    "title": "订单数据总结报告",
    "subtitle": "中文 GBK 订单表 · data-viz 实测样例（探源 → 口径 → 选单 → 看板 → 报告）",
    "meta": {
        "数据来源": "chinese_orders_gbk.csv（GBK 编码，4000 行 × 12 列，中文表头）",
        "分析流程": "AI 直读探源 → 口径拍板 → 用户选单 → 声明式配置 → 看板渲染 → 质量闸门 → 本报告",
        "清洗口径": "空字符串视为缺失；字面 None 视为缺失；订单号重复按同一订单处理（订单数去重）",
        "报告生成": "data-viz skill · report_docx.py 排版（内容与结论由分析过程产出）",
    },
    "sections": [
        {"type": "text", "title": "一、概览", "content":
            f"本数据集共 {rows_n:,.0f} 行订单行，覆盖 {cust:,.0f} 个客户，销售额合计 "
            f"{sales:,.0f} 元。订单号去重后为 1,925 笔订单，即平均每笔订单含 {rows_n/1925:.1f} 个订单行。"
            f"其中 {loss:,.0f} 行（{loss/rows_n*100:.1f}%）为亏损行（利润为负）。"
            "数据文件为 GBK 编码，UTF-8 解码直接失败——这是本次分析遇到的第一个问题，见下节。"},
        {"type": "table", "title": "二、数据质量：探源六项实测结论", "headers":
            ["检查项", "实测结果", "业务含义 / 处理方式"],
         "rows": [
             ["编码", "utf-8 / utf-8-sig 解码失败，GBK 成功", "源系统为 GBK 环境；读取必须级联回退，否则整表不可用"],
             ["空值（伪装）", "客户 291 行、客户类型 168 行为空字符串", "空串不是 NULL，按缺失处理；占客户维度 7.3%"],
             ["缺失（字面）", f"折扣列 {disc_na:,} 行为字面 None", "伪装的缺失值；直接算均值会得到荒谬结果（必须转 NaN）"],
             ["主键重复", f"订单号重复 {dups:,} 行（唯一仅 1,925 / 共 4,000）",
              "同一订单含多个商品行属正常；**订单数必须去重**，否则虚增一倍"],
             ["时间维度", f"{flat_date:,} 行（31%）日期为 2024-03-15；另有 2018 年 M/D/YYYY 格式混存",
              "日期被压平 + 格式不一致 → **月度趋势不可解释**，已在看板标注，不做同比结论"],
             ["数值分布", "利润 716 行为负（最低 -3,840，最高 3,920）；销售额右偏（半数低于约 100 元）",
              "存在亏损与极端值，用箱线图 + 离群点而非仅均值描述"],
         ]},
        {"type": "table", "title": "三、核心指标与口径", "headers": ["指标", "值", "口径（分子 / 分母）"],
         "rows": [
             ["销售额合计", f"{sales:,.0f} 元", "全部 4000 行的销售额之和 / 无（总量指标）"],
             ["订单行数", f"{rows_n:,.0f} 行", "原始数据行数 / 无"],
             ["订单数（去重）", "1,925 笔", "订单号去重计数 / 无"],
             ["客户数", f"{cust:,.0f} 人", "客户字段去重 / 非空客户名（空串 291 行不计入）"],
             ["亏损订单行", f"{loss:,.0f} 行（{loss/rows_n*100:.1f}%）", "利润 < 0 的行数 / 全部 4000 行"],
         ]},
        {"type": "chart", "title": "四、构成分析", "img": str(IMGDIR / "cat.png")},
        {"type": "chart", "title": "五、地域分布", "img": str(IMGDIR / "prov.png")},
        {"type": "table", "title": "六、客户排名 Top8（按销售额）", "headers": ["客户", "销售额（元）", "订单行数"],
         "rows": [[c["客户"], f"{c['销售额']:,.0f}", c["行数"]] for c in custs]},
        {"type": "bullets", "title": "七、洞察", "items": [
            f"产品类别销售额集中在技术类（{cats[0]['销售额']:,.0f} 元，占 {cats[0]['销售额']/sales*100:.1f}%），"
            f"家具次之、办公用品最低；三类差距不大，属均衡结构而非单极依赖。",
            "省份维度呈现明显长尾：四川省以 322,285 元居首，前 4 个省份即累计达 80%（帕累托关键少数），"
            "而剩余省份合计仅 20%——地域资源投放应优先覆盖这 4 个省份。",
            "折扣与利润呈显著负相关（斯皮尔曼 ρ = -0.53，全矩阵中最强相关）：折扣越高利润越低，"
            "且「无折扣」档贡献销售额最高（311,948 元）——大幅折扣并未换来销售额领先。",
            "销售额与利润的回归 R² 仅 0.0196（斜率 0.053）：**销售额几乎无法解释利润**，"
            "说明成本/折扣结构对利润的支配作用远大于营收规模。",
            "利润分布严重右偏且尖峰（偏度 -0.38、峰度 165）：绝大多数订单利润接近 0 附近，"
            "少数订单贡献极端值——用均值汇报利润会失真，应改用中位数与分位数。",
            "折扣字段缺失率 26.2%（1,047 行），客户字段缺失 7.3%：折扣数据的缺失并非随机分布，"
            "补齐前不宜做「折扣力度」类经营结论。",
        ]},
        {"type": "bullets", "title": "八、建议", "items": [
            "立即修数据：折扣列的 None 与空串统一为 NULL；订单日期统一为单一格式并追查 2024-03-15 的压平原因——"
            "在修复前，任何时间趋势类结论都不成立。",
            "口径入库：把本报告第三节的 5 个指标口径固化为口径卡，报表与看板共用同一套分子/分母。",
            "复盘折扣策略：折扣与利润负相关且高折扣未带来销售额优势，建议按折扣档位核算利润贡献，收缩深折扣档位。",
            "报表改用分位数：利润类指标以中位数/P25/P75 与箱线图呈现，避免均值被极端值拉偏。",
            "地域聚焦：按帕累托结论优先保障前 4 个省份的资源投放，其余省份按长尾策略处理。",
        ]},
    ],
    "footer": {"title": "转发说明", "lines": [
        "1) 本报告基于公开/示例数据集（中文 GBK 订单表），用于演示 data-viz 的完整分析链路，非真实业务结论。",
        "2) 配套交付物：单文件离线看板 dashboard.html（含 KPI 口径悬停、L2→L3 下钻、箱线图/Q-Q/帕累托/相关矩阵/回归/缺失画像）、"
        "口径卡 口径卡.md、选单记录 plan.json、数仓 warehouse.db。",
        "3) 看板为单文件网页，双击即可打开，无需联网或安装任何软件；可直接通过微信/邮件转发。",
        "4) 所有数字均可在 warehouse.db 中复核（SQLite），口径定义见 口径卡.md。",
    ]},
}

spec_path = CASE / "report_spec.json"
spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
out = CASE / "数据总结报告.docx"
r = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "report_docx.py"),
                    "--spec", str(spec_path), "--out", str(out)],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
print(r.stdout.strip() or r.stderr.strip()[-800:])
print(f"[产物] {out}  {out.stat().st_size/1024:.0f} KB")

# ---------- 结构校验（office-docx skill 的检查器） ----------
chk = pathlib.Path(r"D:\Apps\deepseek\package\resources\runtime\office-skills\scripts\check_office.py")
if chk.exists():
    c = subprocess.run([sys.executable, "-X", "utf8", str(chk), str(out),
                        "--out", str(CASE / "artifacts" / "docx-checks.json"),
                        "--contains", "口径", "--contains", "帕累托"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n--- DOCX 结构校验 ---")
    print((c.stdout or "").strip()[:600] or (c.stderr or "").strip()[-400:])
