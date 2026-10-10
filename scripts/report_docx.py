#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data-viz: report_docx.py - standard data summary report generator
AI writes the spec (narrative, findings, calibers); this module renders the docx.
Spec: {"title", "subtitle", "meta": {k:v}, "sections": [{type: table|chart|bullets|text, title, ...}]}
"""
import os, sys, json

def render_report(spec, out_path):
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    doc = Document()
    doc.styles["Normal"].font.name = "Microsoft YaHei"
    doc.styles["Normal"].font.size = Pt(10.5)
    doc.add_heading(spec.get("title", "数据总结报告"), level=0)
    if spec.get("subtitle"):
        p = doc.add_paragraph()
        r = p.add_run(spec["subtitle"]); r.bold = True
        r.font.color.rgb = RGBColor(0x14, 0x56, 0xF0)
    meta = spec.get("meta") or {}
    if meta:
        t = doc.add_table(rows=len(meta), cols=2); t.style = "Light Grid Accent 1"
        for i, (k, v) in enumerate(meta.items()):
            t.rows[i].cells[0].text = str(k); t.rows[i].cells[1].text = str(v)
    for sec in spec.get("sections", []):
        if sec.get("title"): doc.add_heading(sec["title"], level=1)
        st = sec.get("type")
        if st == "table":
            hs = sec["headers"]; rows = sec["rows"]
            t = doc.add_table(rows=len(rows)+1, cols=len(hs)); t.style = "Light Grid Accent 1"
            for j, h in enumerate(hs): t.rows[0].cells[j].text = str(h)
            for i, row in enumerate(rows, start=1):
                for j, v in enumerate(row): t.rows[i].cells[j].text = str(v)
        elif st == "chart":
            doc.add_picture(sec["img"], width=Cm(15.5))
        elif st == "bullets":
            for b in sec["items"]: doc.add_paragraph(str(b), style="List Bullet")
        else:
            doc.add_paragraph(str(sec.get("content", "")))
    if spec.get("footer"):
        doc.add_heading(spec["footer"].get("title", "转发说明"), level=1)
        for line in spec["footer"].get("lines", []): doc.add_paragraph(str(line))
    doc.save(out_path)
    return out_path

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    print("saved:", render_report(spec, a.out))