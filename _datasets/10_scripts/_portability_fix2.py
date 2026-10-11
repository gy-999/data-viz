"""收尾：修 example_quickstart.py 的残留绝对路径 + 把 HERE 定义提到使用之前。"""
import pathlib
import re

SKILL = pathlib.Path(r"C:\Users\guoyu\.dsh\skills\data-viz")
p = SKILL / "examples" / "example_quickstart.py"
s = p.read_text(encoding="utf-8-sig")          # 吃掉 BOM
orig = s

# 1) 删除散落各处的 HERE 定义
s = re.sub(r"^.*HERE = Path\(__file__\)\.resolve\(\)\.parent\s*$", "", s, flags=re.M)

# 2) 剩下的绝对路径字面量 -> 相对定位（支持单双引号、raw 前缀）
def repl(m):
    tail = m.group(1).replace("\\\\", "/").replace("\\", "/")
    parts = [x for x in tail.split("/") if x]
    expr = "HERE.parent"
    for x in parts:
        expr += f' / "{x}"'
    return f"str({expr})"

s = re.sub(r"""r?['"]C:(?:\\\\|\\\\)Users(?:\\\\|\\)guoyu(?:\\\\|\\)\.dsh(?:\\\\|\\)skills(?:\\\\|\\)data-viz(?:\\\\|\\)?([^'"]*)['"]""",
           repl, s)

# 3) 统一的 HERE 定义放在最前面（import 之后）
if "from pathlib import Path" not in s:
    s = s.replace("import os, sys, json", "import os, sys, json\nfrom pathlib import Path")
s = s.replace("from pathlib import Path\n", "from pathlib import Path\n\n# 可移植定位：以本文件所在目录为锚点（v3）\nHERE = Path(__file__).resolve().parent\n", 1)

# 4) 清掉多余空行
s = re.sub(r"\n{3,}", "\n\n", s)

p.write_text(s, encoding="utf-8")
print("[rewritten] examples/example_quickstart.py")
print("--- 结果 ---")
for i, ln in enumerate(s.splitlines(), 1):
    if re.search(r"HERE|data-viz|C:\\\\|out_dir|sys\.path|os\.chdir", ln):
        print(f"  {i:>3}  {ln.strip()[:120]}")

print("\n=== 全仓最终复查（绝对路径 / BOM） ===")
pat = re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:\\|/Users/|/home/")
hits = []
for f in list(SKILL.rglob("*.py")) + list(SKILL.rglob("*.md")):
    txt = f.read_text(encoding="utf-8", errors="replace")
    for i, ln in enumerate(txt.splitlines(), 1):
        if pat.search(ln) and not any(k in ln for k in ("os.environ", "你的数据", "DATA_VIZ")):
            hits.append(f"{f.relative_to(SKILL)}:{i}: {ln.strip()[:100]}")
print("\n".join(hits) if hits else "（无机器相关绝对路径，可移植）")
