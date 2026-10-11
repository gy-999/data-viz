"""把 v3 引擎改造重新应用到渲染引擎（幂等、可重复执行、带断言）。

背景：上一轮为清理残留路径误用 git checkout，把本次改造一起还原了。
本脚本把改动固化为可重复执行的补丁，避免再被 checkout 冲掉。

改动 4 处：
  1) TYPE_DEFAULTS 注册 6 种统计图类型
  2) 新增 _norm_ppf（Acklam 正态分位数）
  3) build_comp 新增 6 种类型的载荷构建
  4) 空数据自动隐藏检查覆盖新类型
"""
import pathlib
import sys

GEN = pathlib.Path(r"C:\Users\guoyu\.dsh\skills\data-viz\scripts\render_universal_dashboard.py")
s = GEN.read_text(encoding="utf-8")
orig = s
applied = []

# ---------- 1) TYPE_DEFAULTS ----------
OLD_TYPES = '''    "kpi": (6, 5), "line": (16, 6), "bar": (8, 6), "pie": (8, 8),
    "heatmap": (24, 10), "table": (24, 9), "histogram": (12, 6),
    "text": (24, 2), "heading": (24, 1),
    "area_stack": (16, 6), "scatter": (12, 6), "funnel": (16, 6), "bullet": (8, 5),
    "waterfall": (16, 7), "sankey": (16, 8), "radar": (8, 7), "gauge": (8, 5),
}'''
NEW_TYPES = '''    "kpi": (6, 5), "line": (16, 6), "bar": (8, 6), "pie": (8, 8),
    "heatmap": (24, 10), "table": (24, 9), "histogram": (12, 6),
    "text": (24, 2), "heading": (24, 1),
    "area_stack": (16, 6), "scatter": (12, 6), "funnel": (16, 6), "bullet": (8, 5),
    "waterfall": (16, 7), "sankey": (16, 8), "radar": (8, 7), "gauge": (8, 5),
    # 统计分析扩展（v4）：箱线图 / 正态QQ / 帕累托 / 缺失值画像 / 相关矩阵 / 回归散点
    "box": (12, 6), "qq": (12, 6), "pareto": (16, 7),
    "missing": (12, 6), "corr": (12, 7), "regress": (12, 6),
}'''
if '"box": (12, 6)' not in s:
    assert OLD_TYPES in s, "TYPE_DEFAULTS 锚点未找到"
    s = s.replace(OLD_TYPES, NEW_TYPES)
    applied.append("TYPE_DEFAULTS +6 类型")

# ---------- 2) _norm_ppf ----------
NORM_FN = '''def _norm_ppf(p):
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
        return (((((c[0] * q_ + c[1]) * q_ + c[2]) * q_ + c[3]) * q_ + c[4]) * q_ + c[5]) / \\
               ((((d[0] * q_ + d[1]) * q_ + d[2]) * q_ + d[3]) * q_ + 1)
    if p > phigh:
        q_ = (-2 * _m.log(1 - p)) ** 0.5
        return -(((((c[0] * q_ + c[1]) * q_ + c[2]) * q_ + c[3]) * q_ + c[4]) * q_ + c[5]) / \\
               ((((d[0] * q_ + d[1]) * q_ + d[2]) * q_ + d[3]) * q_ + 1)
    q_ = p - 0.5
    r_ = q_ * q_
    return (((((a[0] * r_ + a[1]) * r_ + a[2]) * r_ + a[3]) * r_ + a[4]) * r_ + a[5]) * q_ / \\
           (((((b[0] * r_ + b[1]) * r_ + b[2]) * r_ + b[3]) * r_ + b[4]) * r_ + 1)


def parse_caliber_cards(kal_path):'''
if "def _norm_ppf(" not in s:
    assert "def parse_caliber_cards(kal_path):" in s
    s = s.replace("def parse_caliber_cards(kal_path):", NORM_FN, 1)
    applied.append("_norm_ppf 正态分位数")

# ---------- 3) build_comp 新类型 ----------
ANCHOR3 = '''        if t == "text": return {"content":d.get("content","")}
        if t == "heading": return {"content":d.get("content","")}
'''
BLOCK3 = ANCHOR3 + open(pathlib.Path(__file__).resolve().parent / "_v3_builders.py", encoding="utf-8").read()
if 'if t == "box":' not in s:
    assert ANCHOR3 in s, "build_comp 锚点未找到"
    s = s.replace(ANCHOR3, BLOCK3, 1)
    applied.append("build_comp +6 类型载荷")

# ---------- 4) 空数据隐藏 ----------
OLD_EMPTY = '''                    (t == "radar" and not data.get("series")) or                     (t == "funnel" and not data.get("stages"))'''
NEW_EMPTY = OLD_EMPTY + ''' or                     (t == "box" and not data.get("groups")) or                     (t == "qq" and not data.get("points")) or                     (t == "pareto" and not data.get("values")) or                     (t == "missing" and not data.get("overall")) or                     (t == "corr" and not data.get("matrix")) or                     (t == "regress" and not data.get("points"))'''
if 't == "pareto" and not data.get("values")' not in s:
    assert OLD_EMPTY in s, "空数据检查锚点未找到"
    s = s.replace(OLD_EMPTY, NEW_EMPTY, 1)
    applied.append("空数据隐藏 +6 类型")

if s != orig:
    GEN.write_text(s, encoding="utf-8")

import py_compile
py_compile.compile(str(GEN), doraise=True)
sys.path.insert(0, str(GEN.parent))
import render_universal_dashboard as R
print("已应用:", applied if applied else "（无改动，已是 v3+）")
print("TYPE_DEFAULTS 类型数:", len(R.TYPE_DEFAULTS))
print("新类型检查:", {k: (k in R.TYPE_DEFAULTS) for k in ("box", "qq", "pareto", "missing", "corr", "regress")})
print("qnorm(0.975) =", round(R._norm_ppf(0.975), 4), "(应为 1.96)")
