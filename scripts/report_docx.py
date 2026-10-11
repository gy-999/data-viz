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


def _soften(text):
    """给超长不可断 token（文件名/路径/URL）插入零宽空格，避免撑破单元格。

    实测问题：`chinese_orders_gbk.csv` 这类长串在固定列宽下不换行，
    文字被顶出表格右边缘（实测 529.4pt > 表格 527.6pt）。
    """
    def _ins(m):
        tok = m.group(0)
        if len(tok) < 12:
            return tok
        return re.sub(r"([._/\-])", "\\1\u200b", tok)   # 注意：替换串里必须用真实字符，不能用 \u 转义
    return re.sub(r"[A-Za-z0-9][A-Za-z0-9._/\-]{11,}", _ins, str(text))


def _table(doc, headers, rows, usable_twips, font_size=None):
    """固定布局表格，总宽严格 = 可用页宽。

    实测踩坑：只设 cell.width / table.width 不够——python-docx 写入的 tblGrid 仍是
    均分宽度，且合计会超出可用页宽（实测 9747 twips vs 可用 9360），导致表格右边
    被裁掉。因此这里显式重建 w:tblGrid 与 w:tblW，并把每列宽度对齐到同一组数值。
    """
    from docx.shared import Twips
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    n = len(headers)
    t = doc.add_table(rows=1, cols=n)
    t.style = "Light Grid Accent 1"
    t.autofit = False

    # 按“显示宽度”分配列宽：中文按 2 个单位算（len() 会把中英文算成同宽，
    # 导致中文表头被挤压、列宽趋近均分——实测问题）。取样 %85 分位，避免被超长值拉爆。
    def _dw(s):
        return sum(2 if ord(c) > 0x2E80 else 1 for c in str(s))

    weights = []
    for i in range(n):
        col_vals = [str(r[i]) for r in rows if i < len(r)]
        col_vals.sort(key=_dw)
        p85 = _dw(col_vals[int(len(col_vals) * 0.85)]) if col_vals else 0
        weights.append(max(_dw(headers[i]), min(p85, 40), 4))
    # 列宽上下限：两列表格首列收紧到 28%（避免“项目”列大片留白），
    # 多列表格单列限制在 10%~45%
    budget = int(usable_twips)
    if n == 2:
        lo, hi = budget * 0.14, budget * 0.28
    else:
        lo, hi = budget * 0.10, budget * 0.45
    widths = [min(max(budget * w / sum(weights), lo), hi) for w in weights]
    scale = budget / sum(widths)
    widths = [max(int(w * scale), 300) for w in widths]
    widths[-1] += budget - sum(widths)          # 余数补给最后一列，确保合计精确

    # 1) 重建 tblGrid
    tbl = t._tbl
    for old in tbl.findall(qn("w:tblGrid")):
        tbl.remove(old)
    grid = OxmlElement("w:tblGrid")
    for w in widths:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(w))
        grid.append(gc)
    tblPr = tbl.tblPr
    tblPr.addnext(grid)

    # 2) 显式 tblW（dxa 绝对值，防止渲染器按内容撑宽）
    for old in tblPr.findall(qn("w:tblW")):
        tblPr.remove(old)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"), str(sum(widths)))
    tblW.set(qn("w:type"), "dxa")
    tblPr.append(tblW)

    # 3) 每行每格 tcW 与 gridCol 对齐
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        _add_inline(cell.paragraphs[0], h, font_size, True)
        _shade(cell, "EEF1F5")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row[:n]):
            cells[i].text = ""
            _add_inline(cells[i].paragraphs[0], _soften(v), font_size)
    for r in t.rows:
        for i, w in enumerate(widths):
            tc = r.cells[i]._tc
            tcPr = tc.get_or_add_tcPr()
            for old in tcPr.findall(qn("w:tcW")):
                tcPr.remove(old)
            tcW = OxmlElement("w:tcW")
            tcW.set(qn("w:w"), str(w))
            tcW.set(qn("w:type"), "dxa")
            tcPr.append(tcW)
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
        s.page_width = Cm(21.0)          # A4：显式固定，避免默认 Letter 导致宽度误判
        s.page_height = Cm(29.7)
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
