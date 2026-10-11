#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data-viz: report_docx.py - standard data summary report generator
AI writes the spec (narrative, findings, calibers); this module renders the docx.
Spec: {"title", "subtitle", "meta": {k:v}, "sections": [{type: table|chart|bullets|text, title, ...}]}

v3.1 修复（实测）：
  - 行内 markdown 解析：**加粗** 与 `代码` 不再以字面星号/反引号出现
  - 中文字体真正生效：run 级显式设置 w:ascii/w:hAnsi/w:eastAsia（原来只改 style，
    正文实际回退到主题字体）
  - 表格固定布局：按可用页宽分配列宽，避免列宽漂移导致中文换行难看
  - 图片按可用页宽自适应，换页面设置不会溢出
"""
import os, sys, json, re

BODY_FONT = "Microsoft YaHei"
MONO_FONT = "Consolas"


def _set_font(run, name=BODY_FONT, size=None, bold=None, color=None):
    """run 级字体设置：同时写 ascii/hAnsi/eastAsia，中文才会真正用这个字体。"""
    from docx.oxml.ns import qn
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = size
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def _add_inline(par, text, size=None, bold=None, color=None):
    """解析 **加粗** 与 `代码`，避免 markdown 语法以字面形式出现。"""
    from docx.shared import RGBColor
    parts = re.split(r"(\*\*.+?\*\*|`[^`]+`)", str(text))
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            _set_font(par.add_run(part[2:-2]), BODY_FONT, size, True, color)
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            _set_font(par.add_run(part[1:-1]), MONO_FONT,
                      None if size is None else size - 0.5, bold, RGBColor(0xC0, 0x39, 0x2B))
        else:
            _set_font(par.add_run(part), BODY_FONT, size, bold, color)
    return par


def _shade(cell, hexcolor):
    from docx.oxml.ns import qn
    pr = cell._element.get_or_add_tcPr()
    pr.append(pr.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:fill"): hexcolor}))


def _table(doc, headers, rows, usable_twips, font_size=None):
    """固定布局表格：按表头文本长度分配列宽，总宽=可用页宽。"""
    from docx.shared import Twips
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.autofit = False
    weights = [max(len(str(h)), 6) for h in headers]
    budget = usable_twips
    widths = [max(int(budget * w / sum(weights)), 700) for w in weights]
    scale = budget / sum(widths)
    widths = [int(w * scale) for w in widths]
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        _add_inline(cell.paragraphs[0], h, font_size, True)
        _shade(cell, "EEF1F5")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row[:len(headers)]):
            cells[i].text = ""
            _add_inline(cells[i].paragraphs[0], v, font_size)
    for r in t.rows:
        for i, w in enumerate(widths):
            r.cells[i].width = Twips(w)
    t.width = Twips(sum(widths))
    return t


def render_report(spec, out_path):
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor, Twips
    from docx.oxml.ns import qn

    doc = Document()
    # 正文样式：显式写 eastAsia，并落到 run 级由 _set_font 保证
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    for name, sz in (("Heading 1", 14), ("Heading 2", 12), ("Title", 22)):
        try:
            st = doc.styles[name]
            st.font.name = BODY_FONT
            st.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
        except KeyError:
            pass
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)
    usable = (doc.sections[0].page_width.twips - doc.sections[0].left_margin.twips
              - doc.sections[0].right_margin.twips)

    h = doc.add_heading("", level=0)
    _add_inline(h, spec.get("title", "数据总结报告"), 22, True, RGBColor(0x1F, 0x23, 0x29))
    if spec.get("subtitle"):
        p = doc.add_paragraph()
        _add_inline(p, spec["subtitle"], 11, True, RGBColor(0x14, 0x56, 0xF0))
    meta = spec.get("meta") or {}
    if meta:
        _table(doc, ["项目", "内容"], [[k, v] for k, v in meta.items()], usable, 10)
    for sec in spec.get("sections", []):
        if sec.get("title"):
            doc.add_heading(str(sec["title"]), level=1)
        st = sec.get("type")
        if st == "table":
            _table(doc, sec["headers"], sec["rows"], usable, 9.5)
        elif st == "chart":
            # 按可用页宽自适应（留 0.2cm 余量），换页面设置也不溢出
            width = min(Cm(15.5), Twips(usable - 113))
            doc.add_picture(sec["img"], width=width)
            doc.add_paragraph()
        elif st == "bullets":
            for b in sec["items"]:
                p = doc.add_paragraph(style="List Bullet")
                _add_inline(p, b, 10.5)
        else:
            p = doc.add_paragraph()
            _add_inline(p, sec.get("content", ""), 10.5)
    if spec.get("footer"):
        doc.add_heading(str(spec["footer"].get("title", "转发说明")), level=1)
        for line in spec["footer"].get("lines", []):
            p = doc.add_paragraph()
            _add_inline(p, line, 10.5)
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    print("saved:", render_report(spec, a.out))
