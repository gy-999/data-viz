#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sql_parser.py - Extract rows from MySQL INSERT VALUE scripts"""
import sys, json

def parse_sql_insert(path, max_rows=5000):
    import io
    # Try until we find the right encoding
    content = None
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'gbk', 'gb18030']:
        try:
            if path.endswith('.gz'):
                import gzip
                f = gzip.open(path, 'rt', encoding=enc, errors='replace')
            else:
                f = open(path, 'r', encoding=enc, errors='replace')
            content = f.read()
            f.close()
            break
        except: pass
    if content is None:
        return {'status':'error','msg':'cannot decode'}
    
    total_inserts = content.upper().count('INSERT')
    pos = content.find('INSERT INTO')
    count = 0; rows = 0; samples = []
    while pos >= 0 and rows < max_rows:
        vs = content.find('VALUES', pos)
        if vs < 0: break
        vp = content.find('(', vs)
        if vp < 0: break
        depth, j = 1, vp + 1
        while j < len(content) and depth > 0:
            c = content[j]
            if c == '(' and (j==0 or content[j-1]!='\\'): depth += 1
            elif c == ')' and (j==0 or content[j-1]!='\\'): depth -= 1
            j += 1
        if depth == 0:
            row_s = content[vp+1:j-1]
            fields = _parse_row(row_s)
            if fields:
                rows += 1
                samples.append(fields)
        pos = content.find('INSERT INTO', j)
        count += 1
    
    cols = ['c'+str(i+1) for i in range(len(samples[0]))] if samples else []
    mb = round(len(content.encode('utf-8')) / 1024 / 1024, 2)
    return {
        'status': 'ok',
        'path': path,
        'total_inserts': total_inserts,
        'rows_parsed': rows,
        'num_fields': len(cols),
        'columns': cols,
        'file_size_mb': mb,
        'is_large': total_inserts > 100000,
        'preview': [[str(v)[:40] for v in r[:10]] for r in samples[:10]]
    }

def _parse_row(s):
    fields = []; i = 0; n = len(s)
    while i < n:
        c = s[i]
        if c in ' \\t\\n\\r': i+=1; continue
        if c == "'":
            j=i+1; buf=[]
            while j < n:
                if s[j]=="'":
                    if j+1<n and s[j+1]=="'": buf.append("'"); j+=2
                    else: j+=1; break
                else: buf.append(s[j]); j+=1
            fields.append(''.join(buf)); i=j
        elif c in '-0123456789.':
            j=i
            while j<n and s[j] not in ',)': j+=1
            fields.append(s[i:j]); i=j
        elif s[i:i+4].upper()=='NULL': fields.append(None); i+=4
        elif c==',': i+=1
        else: i+=1
    return fields

if __name__ == '__main__':
    for path in sys.argv[1:]:
        if path.startswith('--'): continue
        r = parse_sql_insert(path)
        print(json.dumps(r, ensure_ascii=False, default=str, indent=2))

