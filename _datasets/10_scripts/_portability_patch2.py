"""第二批可移植性修补：把 examples 里指向 skill 自身的绝对路径改成 Path(__file__) 相对定位。"""
import pathlib
import re

SKILL = pathlib.Path(r"C:\Users\guoyu\.dsh\skills\data-viz")
ROOT_RE = re.compile(r'["\']C:\\\\Users\\\\guoyu\\\\.dsh\\\\skills\\\\data-viz\\\\([^"\']*)["\']')
ROOT_RE2 = re.compile(r'["\']C:\\Users\\guoyu\\.dsh\\skills\\data-viz\\([^"\']*)["\']')

HEADER = ('# 可移植定位：以本文件所在目录为锚点，换机器/换用户名都不用改（v3）\n'
          'HERE = Path(__file__).resolve().parent\n')

def rel_expr(tail):
    parts = [p for p in tail.replace("\\\\", "/").replace("\\", "/").split("/") if p]
    expr = "HERE.parent"
    for p in parts:
        expr += f' / "{p}"'
    return f"str({expr})"

for name in ("example_well_pipeline.py", "example_odf_pipeline.py", "example_quickstart.py"):
    p = SKILL / "examples" / name
    s = p.read_text(encoding="utf-8")
    orig = s
    n1 = len(ROOT_RE.findall(s)) + len(ROOT_RE2.findall(s))
    s = ROOT_RE.sub(lambda m: rel_expr(m.group(1)), s)
    s = ROOT_RE2.sub(lambda m: rel_expr(m.group(1)), s)
    # 确保有 HERE 定义且 Path 已导入
    if "HERE = Path(__file__).resolve().parent" not in s:
        if "from pathlib import Path" not in s:
            s = s.replace("import gzip, csv, json, os, re, sqlite3, subprocess, sys, shutil",
                          "import gzip, csv, json, os, re, sqlite3, subprocess, sys, shutil\nfrom pathlib import Path")
            if "from pathlib import Path" not in s:
                s = s.replace("import sys, json, os", "import sys, json, os\nfrom pathlib import Path")
        m = re.search(r"^(FENCE|data_dir|out_dir)\s*=", s, re.M)
        if m:
            s = s[:m.start()] + HEADER + "\n" + s[m.start():]
        else:
            s = HEADER + s
    if s != orig:
        p.write_text(s, encoding="utf-8")
        print(f"[patched] examples/{name}  ({n1} 处绝对路径 -> 相对定位)")
    else:
        print(f"[skip]    examples/{name}")

print("\n=== 复查全仓 ===")
pat = re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:\\|/Users/|/home/")
hits = []
for f in list(SKILL.rglob("*.py")) + list(SKILL.rglob("*.md")) + list(SKILL.rglob("*.html")):
    for i, ln in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if pat.search(ln) and "os.environ" not in ln and "你的数据" not in ln and "DATA_VIZ" not in ln:
            hits.append(f"{f.relative_to(SKILL)}:{i}: {ln.strip()[:110]}")
print("\n".join(hits) if hits else "（无机器相关绝对路径残留，可移植）")
