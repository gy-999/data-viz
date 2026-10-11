"""把 skill 里残留的硬编码绝对路径改成可移植写法（幂等，可重复运行）。"""
import pathlib
import re

SKILL = pathlib.Path(r"C:\Users\guoyu\.dsh\skills\data-viz")
changed = []

def patch(rel, pairs, note):
    p = SKILL / rel
    s = p.read_text(encoding="utf-8")
    orig = s
    for old, new in pairs:
        if old and old in s:
            s = s.replace(old, new)
    if s != orig:
        p.write_text(s, encoding="utf-8")
        changed.append(f"{rel}  <- {note}")
        print(f"[patched] {rel}  ({note})")
    else:
        print(f"[skip]    {rel}  (无需改动)")

HOME = r"C:\Users\guoyu\.dsh\skills\data-viz"

# ---- build_resource_dashboard.py：唯一的 view_dict 绝对路径 + 两个子进程脚本路径 ----
patch("scripts/build_resource_dashboard.py", [
    ('vd = json.load(open(r"D:\\\\study\\\\NewPeople\\\\data\\\\data-viz\\\\output\\\\well_dashboard_v2\\\\view_dict.json", encoding="utf-8"))',
     'HERE = Path(__file__).resolve().parent\n'
     '_vd_path = Path(os.environ.get("VIEW_DICT", HERE.parent / "output" / "well_dashboard_v2" / "view_dict.json"))\n'
     'vd = json.load(open(_vd_path, encoding="utf-8")) if _vd_path.exists() else {}'),
    (r'rp = r"D:\\study\\NewPeople\\data\\data-viz\\scripts\\render_universal_dashboard.py"',
     'rp = str(HERE / "render_universal_dashboard.py")'),
    (r'r"D:\\study\\NewPeople\\data\\data-viz\\scripts\\dashboard_check.py"',
     'str(HERE / "dashboard_check.py")'),
], "硬编码路径 → Path(__file__) 相对定位")

# ---- examples：允许用环境变量覆盖数据/输出目录（默认仍是占位符，不写死机器） ----
for name in ("example_well_pipeline.py", "example_odf_pipeline.py"):
    p = SKILL / "examples" / name
    s = p.read_text(encoding="utf-8")
    orig = s
    if "os.environ.get('DATA_VIZ_DATA_DIR'" not in s:
        s = re.sub(
            r'^data_dir = r"(.*)"$',
            lambda m: (
                "# 数据目录：默认占位符，可用环境变量覆盖 ->  $env:DATA_VIZ_DATA_DIR=\"D:\\你的数据\\ZJsftp\\...\"\n"
                f'data_dir = os.environ.get("DATA_VIZ_DATA_DIR", r"{m.group(1)}")'
            ),
            s, count=1, flags=re.M)
        s = re.sub(
            r'^out_dir = r"(.*)"$',
            lambda m: f'out_dir = os.environ.get("DATA_VIZ_OUT_DIR", r"{m.group(1)}")',
            s, count=1, flags=re.M)
    if s != orig:
        p.write_text(s, encoding="utf-8")
        changed.append(f"examples/{name}  <- 参数化")
        print(f"[patched] examples/{name}  (data_dir/out_dir 支持环境变量覆盖)")

small = "\n".join(changed) if changed else "（无改动）"
print("\n=== 本次改动 ===")
print(small)

# 复查：全仓还有哪些绝对路径残留
print("\n=== 复查：仍存在的机器相关绝对路径 ===")
pat = re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:\\|/Users/|/home/")
hits = []
for f in SKILL.rglob("*.py"):
    for i, ln in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if pat.search(ln) and "os.environ" not in ln and "你的数据" not in ln:
            hits.append(f"{f.relative_to(SKILL)}:{i}: {ln.strip()[:110]}")
print("\n".join(hits) if hits else "（仅剩占位符/环境变量默认值，可移植）")
