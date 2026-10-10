
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runner.py — full data-viz pipeline: scan -> analyze -> report"""
import sys, json, os, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_pipeline(source, name=None, output_dir='output', json_mode=False):
    t0 = time.time()
    os.makedirs(output_dir, exist_ok=True)
    
    # STEP 1: Detect
    from scan_preview import auto_preview
    print(f"[1/5] Scanning: {source}", flush=True)
    scan_result = auto_preview(source)
    print(f"  Type: {scan_result.get('source_type',scan_result.get('type','?'))}", flush=True)
    print(f"  Status: {scan_result.get('status','?')}", flush=True)
    
    name = name or scan_result.get('name', 'dataset').rsplit('.',1)[0][:40]
    
    # Save scan result
    scan_path = os.path.join(output_dir, f'{name}_scan.json')
    with open(scan_path, 'w', encoding='utf-8') as f:
        json.dump(scan_result, f, ensure_ascii=False, default=str, indent=2)
    
    # STEP 2: Analyze
    from auto_analyze import auto_analyze
    print(f"[2/5] Analyzing: {name}", flush=True)
    
    # Build simple data rows from scan preview
    preview = scan_result.get('preview', []) or scan_result.get('tables', [])
    if scan_result.get('type') == 'mysql' and scan_result.get('tables'):
        # MySQL: build from table list
        rows = [{'table':t['name'],'rows':t.get('rows',0),'cols':t.get('col_count',0)} for t in scan_result['tables'][:500]]
    elif isinstance(preview, list) and preview:
        rows = preview[:5000]
    else:
        # Fallback: use scan result metadata
        rows = [{'field':k,'value':str(v)[:100]} for k,v in scan_result.get('field_types',{}).items()]              + [{'field':k,'null_rate':str(v.get('rate',0))} for k,v in scan_result.get('null_counts',{}).items()]
    
    stats = auto_analyze(rows, name)
    stats_path = os.path.join(output_dir, f'{name}_stats.json')
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, default=str, indent=2)
    
    # STEP 3: Generate report
    from report_gen import gen_xlsx_report, gen_markdown_report
    print(f"[3/5] Generating reports...", flush=True)
    
    xlsx_path = os.path.join(output_dir, f'{name}_report.xlsx')
    try:
        xl = gen_xlsx_report(stats, xlsx_path)
        print(f"  XLSX: {xl.get('status','?')} -> {xlsx_path}", flush=True)
    except Exception as e:
        print(f"  XLSX err: {e}", flush=True)
    
    md = gen_markdown_report(stats, name)
    md_path = os.path.join(output_dir, f'{name}_summary.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"  MD: OK -> {md_path}", flush=True)
    
    # STEP 4: Caliber cards
    caliber_cards = []
    for c in stats.get('caliber_suggestions',[]):
        caliber_cards.append({
            'field': c['field'],
            'type': c['type'],
            'description': c['description'],
            'questions': c.get('questions',['TBD']),
            '分子': '待确认',
            '分母': '待确认',
            '只算什么': '待确认',
            '不算什么': '待确认',
            '业务方确认': '待签名'
        })
    cal_path = os.path.join(output_dir, f'{name}_caliber-cards.md')
    with open(cal_path, 'w', encoding='utf-8') as f:
        f.write(f'# {name} 口径卡清单\n\n')
        f.write(f'> 生成时间: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n')
        for c in caliber_cards:
            f.write(f'## 口径卡: {c["field"]}\n\n')
            f.write(f'- **类型**: {c["type"]}\n')
            f.write(f'- **描述**: {c["description"]}\n')
            f.write(f'- **待回答**: {"; ".join(c["questions"])}\n')
            f.write(f'- **分子**: {c["分子"]}\n')
            f.write(f'- **分母**: {c["分母"]}\n')
            f.write(f'- **只算什么**: {c["只算什么"]}\n')
            f.write(f'- **不算什么**: {c["不算什么"]}\n')
            f.write(f'- **业务方确认**: {c["业务方确认"]}\n\n')
    print(f"  Caliber: -> {cal_path}", flush=True)
    
    elapsed = round(time.time()-t0, 2)
    result = {
        'status': 'ok',
        'name': name,
        'source': source,
        'source_type': scan_result.get('source_type', scan_result.get('type', '?')),
        'elapsed_sec': elapsed,
        'outputs': {
            'scan': scan_path,
            'stats': stats_path,
            'xlsx': xlsx_path,
            'md': md_path,
            'caliber': cal_path,
        },
        'summary': {
            'rows': stats.get('rows', 0),
            'fields': stats.get('fields', 0),
            'metrics_suggested': sum(1 for c in caliber_cards if c['type']=='metric'),
            'dimensions_found': sum(1 for c in caliber_cards if c['type']=='dimension'),
        }
    }
    
    print(f"[4/5] Elapsed: {elapsed}s", flush=True)
    print(f"[5/5] Outputs:", flush=True)
    for k, v in result['outputs'].items():
        exists = os.path.isfile(v)
        sz = os.path.getsize(v) if exists else 0
        print(f"  {k}: {'OK' if exists else 'MISSING'} ({sz:,} bytes)", flush=True)
    
    return result

if __name__ == '__main__':
    import argparse as ap
    p = ap.ArgumentParser()
    p.add_argument('--source', required=True, help='Data source path/URL')
    p.add_argument('--name', help='Dataset name')
    p.add_argument('--output', default='output')
    args = p.parse_args()
    
    r = run_pipeline(args.source, args.name, args.output)
    print('\n' + json.dumps(r, ensure_ascii=False, default=str, indent=2))

