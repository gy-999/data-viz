
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def auto_analyze(data, name="unknown"):
    """Given a list of dict rows (parsed from any source), produce stats + caliber suggestions"""
    if not data or not isinstance(data, list):
        return {'name':name,'status':'no_data','rows':0,'fields':0}
    
    fields = list(data[0].keys()) if data else []
    n_rows = len(data)
    n_cols = len(fields)
    
    # 1. Field type inference
    field_types = {}
    nullable = {}
    enum_values = {}
    for f in fields:
        vals = [str(r.get(f,'')) for r in data if r.get(f) is not None and str(r.get(f,'')).strip() not in ('','\\N','null','NULL')]
        field_types[f] = _infer_field_type(vals)
        nullable[f] = {'nulls': n_rows - len(vals), 'rate': round((n_rows - len(vals))/max(n_rows,1), 4)}
        unique = len(set(vals[:5000]))
        if unique <= 30 and unique > 0 and field_types[f] in ('string','category'):
            enum_values[f] = list(set(vals))[:20]
    
    # 2. Numeric stats
    numeric_stats = {}
    for f in fields:
        if field_types.get(f) in ('int','float'):
            nums = []
            for r in data:
                v = r.get(f)
                if v is not None:
                    try: nums.append(float(v))
                    except: pass
            if nums:
                nums.sort()
                numeric_stats[f] = {
                    'min': nums[0], 'max': nums[-1],
                    'mean': round(sum(nums)/len(nums), 4),
                    'median': nums[len(nums)//2],
                    'q25': nums[len(nums)//4],
                    'q75': nums[3*len(nums)//4],
                    'sum': round(sum(nums), 4),
                    'count': len(nums)
                }
    
    # 3. Category distribution
    cat_dist = {}
    for f in fields:
        if field_types.get(f) in ('category','string'):
            dist = {}
            for r in data:
                v = str(r.get(f,''))[:80]
                if v and v not in ('','\\N','null','NULL'):
                    dist[v] = dist.get(v, 0) + 1
            if len(dist) <= 30 and dist:
                sorted_d = sorted(dist.items(), key=lambda x:-x[1])
                cat_dist[f] = [{'value':k,'count':v,'pct':round(v/n_rows*100,1)} for k,v in sorted_d[:15]]
    
    # 4. Time range detection
    time_range = {}
    for f in fields:
        if field_types.get(f) == 'datetime':
            vals = [str(r.get(f,'')) for r in data if r.get(f)]
            if vals:
                vals.sort()
                time_range[f] = {'from': vals[0][:10], 'to': vals[-1][:10], 'count': len(vals)}
    
    # 5. Caliber suggestions
    caliber_suggestions = []
    seen_suggestions = set()
    for f in fields:
        ft = field_types.get(f, '')
        # Suggest metrics for numeric fields
        if ft in ('int','float') and numeric_stats.get(f):
            name_en = f.replace(' ','_').lower()[:40]
            suggestion = {
                'field': f,
                'type': 'metric',
                'suggested_name': name_en,
                'description': f'[{f}] 数值字段 - 建议明确口径',
                'questions': [
                    f'这个字段{f}的{"%d" % nullable.get(f,{}).get("nulls",0)}条空值({nullable.get(f,{}).get("rate",0)*100:.0f}%)怎么处理？算0还是排除？',
                    f'聚合规则是什么（SUM/AVG/COUNT）？'
                ]
            }
            # Dedup by field
            key = ('metric', f)
            if key not in seen_suggestions:
                seen_suggestions.add(key)
                caliber_suggestions.append(suggestion)
        
        # Suggest dimensions for category/string fields
        if ft in ('category','string') and cat_dist.get(f):
            suggestion = {
                'field': f,
                'type': 'dimension',
                'suggested_name': f,
                'description': f'[{f}] 分类字段（{len(cat_dist[f])}个取值）',
                'questions': [
                    f'字段{f}的含义是什么？',
                    f'有哪些取值需要合并/排除？'
                ]
            }
            key = ('dimension', f)
            if key not in seen_suggestions:
                seen_suggestions.add(key)
                caliber_suggestions.append(suggestion)
    
    return {
        'name': name,
        'status': 'ok',
        'rows': n_rows,
        'fields': n_cols,
        'field_types': field_types,
        'nullable': nullable,
        'enum_values': enum_values,
        'numeric_stats': numeric_stats,
        'cat_distribution': cat_dist,
        'time_range': time_range,
        'caliber_suggestions': caliber_suggestions,
    }

def _infer_field_type(vals):
    if not vals: return 'empty'
    n = min(len(vals), 200)
    try:
        for v in vals[:n]: int(v)
        return 'int'
    except: pass
    try:
        for v in vals[:n]: float(v)
        return 'float'
    except: pass
    import datetime as dt
    for pat in ['%Y-%m-%d','%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M:%S.%f','%Y/%m/%d']:
        m = sum(1 for v in vals[:n] if _try_parse(v, pat))
        if m >= n * 0.7: return 'datetime'
    u = len(set(vals[:500]))
    return 'category' if u <= 20 else 'text' if sum(len(v) for v in vals[:200])/max(len(vals[:200]),1) > 100 else 'string'

def _try_parse(v, pat):
    from datetime import datetime
    try: datetime.strptime(v.strip(), pat); return True
    except: return False

if __name__ == '__main__':
    import argparse as ap
    p = ap.ArgumentParser()
    p.add_argument('--data', help='JSON data file path')
    p.add_argument('--name', default='dataset')
    args = p.parse_args()
    if args.data:
        with open(args.data, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        rows = raw if isinstance(raw, list) else raw.get('rows', raw.get('data', []))
        result = auto_analyze(rows, args.name)
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
    else:
        print("auto_analyze: core analysis engine loaded. Provide --data to run.")

