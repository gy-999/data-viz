#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sql_parser.py - Extract rows from MySQL INSERT VALUE scripts"""
import sys, json, re, re, re, re

def parse_sql_insert(path, max_rows=5000):
    """Extract data rows from SQL INSERT scripts (supports bulk multi-tuple INSERT)"""
    content = None
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'gbk', 'gb18030']:
        try:
            opener = gzip.open if path.endswith('.gz') else open
            f = opener(path, 'rt', encoding=enc, errors='replace')
            content = f.read()
            f.close()
            break
        except Exception:
            try: f.close()
            except Exception: pass
    if content is None:
        return {'status': 'error', 'msg': 'cannot decode'}

    total_inserts = content.upper().count('INSERT')
    rows = 0; samples = []; per_table = {}
    Qc = "'"; BSc = '\\'
    pos = 0
    while True:
        ii = content.find('INSERT INTO', pos)
        if ii < 0: break
        tbl_m = re.search(r'INSERT INTO\s+`?(\w+)`?', content[ii:ii+200], re.I)
        tbl = tbl_m.group(1) if tbl_m else "?"
        vs = content.find('VALUES', ii)
        if vs < 0: pos = ii + 10; continue
        end = content.find(';', vs)
        if end < 0: end = len(content)
        block = content[vs:end]
        in_str = False; esc = False; depth = 0; start = -1; k = 0
        while k < len(block):
            ch = block[k]
            if in_str:
                if esc: esc = False
                elif ch == BSc: esc = True
                elif ch == Qc: in_str = False
            else:
                if ch == Qc: in_str = True
                elif ch == '(':
                    if depth == 0: start = k
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0 and start >= 0:
                        fields = _parse_row(block[start+1:k])
                        if fields:
                            rows += 1
                            per_table[tbl] = per_table.get(tbl, 0) + 1
                            if rows <= max_rows: samples.append(fields)
                        start = -1
                elif ch == ';' and depth == 0:
                    break
            k += 1
        pos = end
    cols = ['c' + str(i+1) for i in range(len(samples[0]))] if samples else []
    mb = round(len(content.encode('utf-8')) / 1048576, 2)
    return {'status': 'ok', 'path': path, 'total_inserts': total_inserts,
            'rows_parsed': rows, 'num_fields': len(cols), 'columns': cols,
            'per_table': per_table, 'file_size_mb': mb,
            'is_large': total_inserts > 100000,
            'preview': [[str(v)[:40] for v in r[:10]] for r in samples[:10]]}

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

