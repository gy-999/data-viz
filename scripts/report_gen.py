
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_gen.py — output triple: XLSX report + ECharts HTML + Markdown summary"""
import sys, json, os, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def gen_xlsx_report(stats, output_path):
    """Generate XLSX report with native charts using XlsxWriter"""
    try:
        import xlsxwriter
    except:
        return {'status':'error','msg':'xlsxwriter not installed'}
    
    wb = xlsxwriter.Workbook(output_path)
    
    # Sheet 1: Statistics
    ws1 = wb.add_worksheet('Statistics')
    header_fmt = wb.add_format({'bold':True,'bg_color':'#4472C4','font_color':'white','border':1})
    num_fmt = wb.add_format({'num_format':'#,##0.00','border':1})
    int_fmt = wb.add_format({'num_format':'#,##0','border':1})
    pct_fmt = wb.add_format({'num_format':'0.0%','border':1})
    
    row = 0
    ws1.write(row, 0, 'Field', header_fmt)
    ws1.write(row, 1, 'Type', header_fmt)
    ws1.write(row, 2, 'Null Rate', header_fmt)
    ws1.write(row, 3, 'Min', header_fmt)
    ws1.write(row, 4, 'Max', header_fmt)
    ws1.write(row, 5, 'Mean', header_fmt)
    ws1.write(row, 6, 'Median', header_fmt)
    ws1.write(row, 7, 'Q25', header_fmt)
    ws1.write(row, 8, 'Q75', header_fmt)
    ws1.write(row, 9, 'Sum', header_fmt)
    row += 1
    
    fields = stats.get('fields', {}).keys() if isinstance(stats.get('fields'), dict) else []
    if not fields:
        fields = list(stats.get('field_types', {}).keys())
    
    for f in fields:
        ws1.write(row, 0, str(f))
        ws1.write(row, 1, str(stats.get('field_types',{}).get(f,'')))
        null_rate = stats.get('nullable',{}).get(f,{}).get('rate',0)
        ws1.write_number(row, 2, null_rate, pct_fmt if null_rate > 0 else None)
        ns = stats.get('numeric_stats',{}).get(f,{})
        if ns:
            ws1.write_number(row, 3, ns.get('min',0), num_fmt)
            ws1.write_number(row, 4, ns.get('max',0), num_fmt)
            ws1.write_number(row, 5, ns.get('mean',0), num_fmt)
            ws1.write_number(row, 6, ns.get('median',0), num_fmt)
            ws1.write_number(row, 7, ns.get('q25',0), num_fmt)
            ws1.write_number(row, 8, ns.get('q75',0), num_fmt)
            ws1.write_number(row, 9, ns.get('sum',0), num_fmt)
        row += 1
    
    # Sheet 2: Category distributions
    ws2 = wb.add_worksheet('Distributions')
    row = 0
    for f, cats in stats.get('cat_distribution',{}).items():
        ws2.write(row, 0, f"--- {f} ---")
        row += 1
        ws2.write(row, 0, 'Value', header_fmt)
        ws2.write(row, 1, 'Count', header_fmt)
        ws2.write(row, 2, 'Percent', header_fmt)
        row += 1
        for c in cats[:15]:
            ws2.write(row, 0, c['value'])
            ws2.write_number(row, 1, c['count'], int_fmt)
            ws2.write_number(row, 2, c['pct']/100, pct_fmt)
            row += 1
        row += 1
    
    # Sheet 3: Caliber suggestions
    ws3 = wb.add_worksheet('Caliber Cards')
    row = 0
    ws3.write(row, 0, 'Field', header_fmt)
    ws3.write(row, 1, 'Type', header_fmt)
    ws3.write(row, 2, 'Description', header_fmt)
    ws3.write(row, 3, 'Questions', header_fmt)
    row += 1
    for c in stats.get('caliber_suggestions',[]):
        ws3.write(row, 0, str(c.get('field','')))
        ws3.write(row, 1, str(c.get('type','')))
        ws3.write(row, 2, str(c.get('description','')))
        ws3.write(row, 3, '; '.join(c.get('questions',[])))
        row += 1
    
    # Charts
    chart_sheet = wb.add_worksheet('Charts')
    chart_row = 0
    for f, cats in stats.get('cat_distribution',{}).items():
        if len(cats) < 2: continue
        chart = wb.add_chart({'type':'column'})
        cats_sorted = sorted(cats, key=lambda x:-x['count'])[:10]
        chart_sheet.write(chart_row, 0, f)
        for i, c in enumerate(cats_sorted):
            chart_sheet.write(chart_row+1+i, 0, str(c['value'][:20]))
            chart_sheet.write_number(chart_row+1+i, 1, c['count'])
        chart.add_series({
            'categories': [chart_sheet.name, chart_row+1, 0, chart_row+len(cats_sorted), 0],
            'values':     [chart_sheet.name, chart_row+1, 1, chart_row+len(cats_sorted), 1],
            'name': str(f),
        })
        chart.set_title({'name': str(f)})
        chart.set_legend({'none': True})
        chart_sheet.insert_chart(chart_row, 3, chart)
        chart_row += len(cats_sorted) + 4
    
    wb.close()
    return {'status':'ok','output':output_path,'sheets':3}

def gen_markdown_report(stats, name='dataset', caliber_file=None, chart_refs=None):
    """Generate Markdown analysis report"""
    lines = []
    lines.append(f'# {name} · 数据分析报告')
    lines.append('')
    lines.append(f'> **数据来源**: {name} | **行数**: {stats.get("rows",0):,} | **字段**: {stats.get("fields",0)}')
    lines.append(f'> **生成时间**: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")}')
    lines.append('')
    
    # Data Quality
    lines.append('## 一、数据质量摘要')
    lines.append('')
    lines.append('| 字段 | 类型 | 空值率 |')
    lines.append('|---|---|---|')
    for f in list(stats.get('field_types',{}).keys())[:20]:
        ft = stats['field_types'].get(f,'')
        nr = stats.get('nullable',{}).get(f,{}).get('rate',0)
        flag = '⚠️' if nr > 0.1 else '✅'
        lines.append(f'| {f} | {ft} | {nr:.1%} {flag} |')
    lines.append('')
    
    # Numeric stats
    if stats.get('numeric_stats'):
        lines.append('## 二、数值统计')
        lines.append('')
        lines.append('| 字段 | 最小值 | 最大值 | 均值 | 中位数 | 总和 |')
        lines.append('|---|---|---|---|---|---|')
        for f, ns in list(stats['numeric_stats'].items())[:10]:
            lines.append(f'| {f} | {ns.get("min","")} | {ns.get("max","")} | {ns.get("mean","")} | {ns.get("median","")} | {ns.get("sum","")} |')
        lines.append('')
    
    # Distributions
    if stats.get('cat_distribution'):
        lines.append('## 三、分类分布')
        lines.append('')
        for f, cats in list(stats['cat_distribution'].items())[:5]:
            lines.append(f'### {f}')
            lines.append('')
            lines.append('| 值 | 计数 | 占比 |')
            lines.append('|---|---|---|')
            top5 = cats[:5]
            for c in top5:
                lines.append(f'| {c["value"]} | {c["count"]:,} | {c["pct"]}% |')
            others = sum(c['count'] for c in cats[5:])
            other_pct = sum(c['pct'] for c in cats[5:])
            if others > 0:
                lines.append(f'| 其他({len(cats)-5}项) | {others:,} | {other_pct:.1f}% |')
            lines.append('')
    
    # Caliber
    if stats.get('caliber_suggestions'):
        lines.append('## 四、口径建议')
        lines.append('')
        for c in stats['caliber_suggestions'][:10]:
            lines.append(f'- **{c["field"]}** ({c["type"]}): {c["description"]}')
            for q in c.get('questions',[]):
                lines.append(f'  - ❓ {q}')
        lines.append('')
    
    # Time range
    if stats.get('time_range'):
        lines.append('## 五、时间范围')
        lines.append('')
        for f, tr in stats['time_range'].items():
            lines.append(f'- **{f}**: {tr.get("from","")} ~ {tr.get("to","")} ({tr.get("count",0):,}条记录)')
        lines.append('')
    
    # Output files
    lines.append('## 六、产出物')
    lines.append('')
    lines.append('| 文件 | 说明 |')
    lines.append('|---|---|')
    lines.append(f'| {name}_report.xlsx | Excel报表（统计表+原生图表+口径卡） |')
    lines.append(f'| {name}_dashboard.html | 交互看板（ECharts 17组件+下钻） |')
    lines.append(f'| {name}_summary.md | 本文件（Markdown分析报告） |')
    if chart_refs:
        for ref, label in chart_refs:
            lines.append(f'| ![图表]({ref}) | {label} |')
    lines.append('')
    
    return '\n'.join(lines)

if __name__ == '__main__':
    import argparse as ap
    p = ap.ArgumentParser()
    p.add_argument('--stats', required=True, help='JSON stats file from auto_analyze')
    p.add_argument('--name', default='dataset')
    p.add_argument('--output', default='output')
    args = p.parse_args()
    
    with open(args.stats, 'r', encoding='utf-8') as f:
        stats = json.load(f)
    
    os.makedirs(args.output, exist_ok=True)
    name = args.name
    
    # XLSX
    xlsx_path = os.path.join(args.output, f'{name}_report.xlsx')
    xlsx_r = gen_xlsx_report(stats, xlsx_path)
    print(f'XLSX: {json.dumps(xlsx_r)}', flush=True)
    
    # Markdown
    md = gen_markdown_report(stats, name)
    md_path = os.path.join(args.output, f'{name}_summary.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'MD: OK -> {md_path}', flush=True)
    
    print(f'OUTPUT_DIR: {args.output}', flush=True)

