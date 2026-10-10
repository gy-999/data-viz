
import os, sys, json
sys.path.insert(0, r'D:\study\NewPeople\data\data-viz\scripts')
os.chdir(r'D:\study\NewPeople\data\data-viz')

from scan_preview import scan
from auto_analyze import auto_analyze
from report_gen import gen_xlsx_report, gen_markdown_report
from datetime import datetime

# 1. Scan MySQL
print("\n[1/3] Scanning MySQL cqcc...")
result = scan("mysql://root:${MYSQL_PASS}@127.0.0.1:3306/cqcc")
print(f"  Tables: {result.get('table_count')}, Total rows: {result.get('total_rows')}")

# 2. Find sa_label table
sa_label = None
for t in result.get('tables', []):
    if t['name'] == 'sa_label':
        sa_label = t
        break

if not sa_label:
    print("ERROR: sa_label not found")
    sys.exit(1)

print(f"\n[2/3] Analyzing sa_label ({sa_label['rows']:,} rows, {sa_label.get('col_count')} cols)")

# Build data for analysis
rows = [{'table': sa_label['name'], 'rows': sa_label['rows'], 'cols': sa_label.get('col_count', 0)}]
stats = auto_analyze(rows, 'sa_label')
print(f"  Fields analyzed: {stats.get('fields')}")
print(f"  Caliber suggestions: {len(stats.get('caliber_suggestions', []))}")

# 3. Generate outputs
print("\n[3/3] Generating reports...")
out_dir = os.path.join(r'D:\study\NewPeople\data\data-viz', 'output')
os.makedirs(out_dir, exist_ok=True)

# XLSX
xlsx_path = os.path.join(out_dir, 'sa_label_report.xlsx')
xl = gen_xlsx_report(stats, xlsx_path)
print(f"  XLSX: {xl.get('status')} -> {xlsx_path}")

# Markdown
md = gen_markdown_report(stats, 'sa_label')
md_path = os.path.join(out_dir, 'sa_label_summary.md')
with open(md_path, 'w', encoding='utf-8') as f:
    f.write(md)
print(f"  MD: OK -> {md_path}")

print(f"\n\n{'='*50}")
print(f"  data-viz 分析完成")
print(f"  输出目录: {out_dir}")
print(f"  耗时: {datetime.now().isoformat()}")
print(f"{'='*50}")
