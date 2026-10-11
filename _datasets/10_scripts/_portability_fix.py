"""修掉上一批替换留下的 `rstr(` 残留（raw 前缀没被吃掉），并复查。"""
import pathlib
import re

SKILL = pathlib.Path(r"C:\Users\guoyu\.dsh\skills\data-viz")
for name in ("example_well_pipeline.py", "example_odf_pipeline.py", "example_quickstart.py"):
    p = SKILL / "examples" / name
    s = p.read_text(encoding="utf-8")
    orig = s
    s = s.replace("rstr(", "str(")
    if s != orig:
        p.write_text(s, encoding="utf-8")
        print(f"[fixed] examples/{name}")

print("\n=== 关键行复查 ===")
for name in ("example_well_pipeline.py", "example_odf_pipeline.py", "example_quickstart.py"):
    p = SKILL / "examples" / name
    print(f"--- {name}")
    for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if re.search(r"^(data_dir|out_dir|rp|shallow)\s*=|HERE|os\.chdir|sys\.path\.insert", ln):
            print(f"  {i:>4}  {ln.strip()[:120]}")
    # 真正的语义检查：不允许出现 rstr / 裸 C:\ 路径
    bad = [ln for ln in p.read_text(encoding="utf-8").splitlines() if "rstr(" in ln]
    print(f"  -> rstr 残留: {len(bad)}")
