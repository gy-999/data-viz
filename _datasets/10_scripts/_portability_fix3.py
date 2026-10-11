"""用可验证的方式修掉最后两处：先测正则，再替换，再断言结果里没有裸盘符路径。"""
import pathlib
import re

SKILL = pathlib.Path(r"C:\Users\guoyu\.dsh\skills\data-viz")
p = SKILL / "examples" / "example_quickstart.py"
s = p.read_text(encoding="utf-8")

# 用最简单的字面量定位（避免正则转义踩坑）
RAW_DOUBLE = r"r'C:\Users\guoyu\.dsh\skills\data-viz'"          # r'C:\Users\...\data-viz'
RAW_DOUBLE_BS = r"'C:\Users\guoyu\.dsh\skills\data-viz'"        # 'C:\Users\...\data-viz'

def targets(line):
    return [t for t in (RAW_DOUBLE, RAW_DOUBLE_BS) if t in line]

print("=== 替换前：命中检查 ===")
for i, ln in enumerate(s.splitlines(), 1):
    t = targets(ln)
    if t:
        print(f"  {i:>3} 命中 {len(t)} 处: {ln.strip()[:100]}")

s2 = s.replace(RAW_DOUBLE, 'str(HERE.parent)').replace(RAW_DOUBLE_BS, 'str(HERE.parent)')

print("\n=== 替换后断言 ===")
assert "C:\\Users" not in s2, "仍有裸盘符路径"
assert "rstr(" not in s2, "又有 rstr 残留"
for i, ln in enumerate(s2.splitlines(), 1):
    if "HERE" in ln or "out_dir" in ln:
        print(f"  {i:>3}  {ln.strip()[:110]}")

p.write_text(s2, encoding="utf-8")
print("\n[written] example_quickstart.py")

# 复查全仓
print("\n=== 全仓最终复查 ===")
pat = re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:\\|/Users/|/home/")
hits = []
for f in list(SKILL.rglob("*.py")) + list(SKILL.rglob("*.md")):
    for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if pat.search(ln) and not any(k in ln for k in ("os.environ", "你的数据", "DATA_VIZ", "r'D:", "D:\\你的")):
            hits.append(f"{f.relative_to(SKILL)}:{i}: {ln.strip()[:100]}")
print("\n".join(hits) if hits else "（无可移植性问题）")
