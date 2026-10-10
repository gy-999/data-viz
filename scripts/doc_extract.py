
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data-viz: doc_extract.py - extract tables & text from docx/pptx/xlsx into CSV
so unstructured documents enter the standard analysis pipeline.
Output: <outdir>/table_N.csv (utf-8-sig, Excel-friendly) + summary JSON
"""
import os, sys, json, csv
from pathlib import Path

def extract_docx(path, outdir):
    from docx import Document
    doc = Document(path)
    csvs = []
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for i, tb in enumerate(doc.tables, 1):
        fp = os.path.join(outdir, "table_%02d.csv" % i)
        with open(fp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            for row in tb.rows:
                w.writerow([c.text.strip() for c in row.cells])
        csvs.append({"file": fp, "rows": len(tb.rows), "cols": len(tb.rows[0].cells) if tb.rows else 0})
    return {"kind": "docx", "paragraphs": len(paras), "chars": sum(len(t) for t in paras),
            "tables": len(doc.tables), "csvs": csvs, "text_preview": paras[:5]}

def extract_pptx(path, outdir):
    from pptx import Presentation
    prs = Presentation(path)
    csvs = []; texts = []
    tno = 0
    for si, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if shape.has_text_frame:
                t = shape.text_frame.text.strip()
                if t: texts.append(t)
            if getattr(shape, "has_table", False) and shape.has_table:
                tno += 1
                fp = os.path.join(outdir, "slide%02d_table_%02d.csv" % (si, tno))
                tb = shape.table
                with open(fp, "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f)
                    for row in tb.rows:
                        w.writerow([c.text.strip() for c in row.cells])
                csvs.append({"file": fp, "rows": len(tb.rows), "cols": len(tb.columns)})
    return {"kind": "pptx", "slides": len(prs.slides), "text_shapes": len(texts),
            "tables": tno, "csvs": csvs, "text_preview": texts[:5]}

def extract_xlsx(path, outdir):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    csvs = []
    for sn in wb.sheetnames:
        ws = wb[sn]
        fp = os.path.join(outdir, "sheet_%s.csv" % re_sub(sn))
        n = 0
        with open(fp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            for row in ws.iter_rows(values_only=True):
                w.writerow(["" if c is None else str(c) for c in row])
                n += 1
                if n >= 100000: break
        csvs.append({"file": fp, "rows": n, "sheet": sn})
    wb.close()
    return {"kind": "xlsx", "sheets": len(csvs), "csvs": csvs}

def re_sub(name):
    import re
    return re.sub(r"[^\w\u4e00-\u9fa5]+", "_", name)[:30] or "sheet"

def extract(source, outdir=None):
    p = Path(source)
    ext = p.suffix.lower()
    outdir = outdir or str(p.parent / (p.stem + "_extracted"))
    os.makedirs(outdir, exist_ok=True)
    if ext == ".docx": r = extract_docx(str(p), outdir)
    elif ext == ".pptx": r = extract_pptx(str(p), outdir)
    elif ext in (".xlsx", ".xlsm"): r = extract_xlsx(str(p), outdir)
    else: raise ValueError("unsupported: " + ext)
    r["source"] = str(p)
    r["outdir"] = outdir
    return r

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--outdir", default=None)
    a = ap.parse_args()
    r = extract(a.source, a.outdir)
    print(json.dumps(r, ensure_ascii=False, indent=2))
