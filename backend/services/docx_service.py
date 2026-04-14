"""Word document report generation service.

Images are inserted INLINE at the exact sentence where （见图N） appears.
All figures are numbered sequentially starting from 图1.
Figure captions are centered beneath each image.

Fixed figure numbering (must match ai_report.py prompt):
  图1  — 气温变化趋势     (chart: 气温趋势)
  图2  — 每日降雨量       (chart: 降雨量)
  图3  — 土壤墒情变化     (chart: 土壤墒情)
  图4  — 每日虫情捕获量   (chart: 虫情日捕获)
  图5  — 虫种捕获统计     (chart: 虫种统计)
  图6  — 孢子捕获趋势     (chart: 孢子趋势)
  图7  — 气象监测现场实景 (gemini: weather / smart_devices / forest_ecology)
  图8  — 病害孢子风险示意 (gemini: disease)
  图9+ — 虫种生态图鉴     (gemini: pests, one per species)
"""

import io
import base64
import os
import re

from docx import Document
from docx.shared import Inches, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
from services.report_figures import (
    build_figure_manifest,
    build_figure_map as build_shared_figure_map,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_page_number(run):
    for tag, text in [
        ('w:fldChar', None), ('w:instrText', "PAGE"), ('w:fldChar', None), ('w:fldChar', None)
    ]:
        el = OxmlElement(tag)
        if text:
            el.set(qn('xml:space'), 'preserve')
            el.text = text
        else:
            ftype = ['begin', 'separate', 'end'].pop(0) if not hasattr(_add_page_number, '_state') else None
        run._r.append(el)

    # simpler version
    for ftype in ('begin', 'separate', 'end'):
        fc = OxmlElement('w:fldChar')
        fc.set(qn('w:fldCharType'), ftype)
        run._r.append(fc)
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = "PAGE"
    run._r.append(instr)


def _set_cjk_font(run, name='Microsoft YaHei', bold=None):
    if bold is not None:
        run.bold = bold
    run.font.name = name
    if run._element.rPr is None:
        run._element.get_or_add_rPr()
    run._element.rPr.rFonts.set(qn('w:eastAsia'), name)


def _set_heading(doc, text, level):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        _set_cjk_font(run, bold=True)
    return p


def _add_paragraph(doc, text, first_indent=True, left_indent=False):
    """Add a paragraph with CJK font and optional indent."""
    p = doc.add_paragraph()
    if first_indent:
        p.paragraph_format.first_line_indent = Pt(24)
    if left_indent:
        p.paragraph_format.left_indent = Pt(24)

    for part in re.split(r'(\*\*.*?\*\*)', text):
        if part.startswith('**') and part.endswith('**'):
            run = p.add_run(part[2:-2])
            _set_cjk_font(run, bold=True)
        else:
            run = p.add_run(part)
            _set_cjk_font(run, bold=False)
    return p


def _insert_figure(doc, b64_data: str, caption: str, width_inches: float = 5.5):
    """Insert an image followed by a centered caption paragraph."""
    try:
        # strip data URI prefix if present
        raw = b64_data.split(',')[-1]
        img_bytes = base64.b64decode(raw)
        pic_para = doc.add_paragraph()
        pic_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = pic_para.add_run()
        run.add_picture(io.BytesIO(img_bytes), width=Inches(width_inches))
    except Exception:
        return

    cap_para = doc.add_paragraph()
    cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_run = cap_para.add_run(caption)
    _set_cjk_font(cap_run, bold=False)
    cap_run.font.size = Pt(10)


def _build_figure_map(
    summary: dict,
    charts: dict,
    ai_images: dict,
    figure_manifest: list[dict] | None = None,
) -> dict[int, tuple[str, str]]:
    """Build {fig_num: (image_data, caption)} from the shared figure manifest."""

    manifest = figure_manifest or build_figure_manifest(summary, charts, ai_images)
    return build_shared_figure_map(manifest)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_docx_report(
    summary: dict,
    ai_analysis: str,
    charts: dict,
    ai_images: dict,
    filepath: str,
    figure_manifest: list[dict] | None = None,
):
    """Generate a Word document with images inserted inline at （见图N） positions."""
    doc = Document()

    # Global styles
    for style_name in ['Normal', 'Heading 1', 'Heading 2', 'Heading 3', 'Title']:
        if style_name in doc.styles:
            s = doc.styles[style_name]
            s.font.name = 'Microsoft YaHei'
            if s.element.rPr is not None:
                s.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')

    # Footer with page numbers
    section = doc.sections[0]
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_cjk_font(fp.add_run("第 "))
    fc_run = fp.add_run()
    # page number field
    for ftype in ('begin', 'separate', 'end'):
        fc = OxmlElement('w:fldChar')
        fc.set(qn('w:fldCharType'), ftype)
        fc_run._r.append(fc)
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = "PAGE"
    fc_run._r.append(instr)
    _set_cjk_font(fp.add_run(" 页"))

    # Title
    period = summary.get("period", {})
    t_start = period.get("start", "")
    t_end = period.get("end", "")
    _set_heading(doc, "三亚市天涯区智慧农业生态监测报告", level=0)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"统计周期：{t_start} 至 {t_end}")
    _set_cjk_font(r)

    # Cover image (no figure number, full width, title page only)
    cover_b64 = ai_images.get("cover")
    if cover_b64:
        try:
            raw = cover_b64.split(',')[-1]
            img_bytes = base64.b64decode(raw)
            cover_para = doc.add_paragraph()
            cover_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cover_para.add_run().add_picture(io.BytesIO(img_bytes), width=Inches(6.0))
        except Exception:
            pass

    doc.add_page_break()

    # Build figure map
    figures = _build_figure_map(summary, charts, ai_images, figure_manifest)

    # Pattern to detect figure references: （见图N） or (见图N) or （图N）
    FIG_REF_RE = re.compile(r'[（(](?:见)?图(\d+)[）)]')

    next_expected_fig = 1

    def _insert_figures_through(target_fig: int) -> None:
        nonlocal next_expected_fig
        while next_expected_fig <= target_fig:
            if next_expected_fig in figures:
                b64, caption = figures[next_expected_fig]
                _insert_figure(doc, b64, caption)
                del figures[next_expected_fig]
            next_expected_fig += 1

    # Render AI analysis and insert figures strictly in numeric order.
    # We do not trust the AI paragraph order because it may mention 图7 before 图5.
    if ai_analysis:
        for line in ai_analysis.split("\n"):
            line = line.strip()
            if not line:
                doc.add_paragraph()
                continue

            if line.startswith("## "):
                _set_heading(doc, line[3:].replace('**', '').strip(), level=1)
            elif line.startswith("### "):
                _set_heading(doc, line[4:].replace('**', '').strip(), level=2)
            elif line.startswith(("- ", "* ", "• ")):
                clean = line[2:].replace('**', '').strip()
                _add_paragraph(doc, f"■ {clean}", first_indent=False, left_indent=True)
            else:
                _add_paragraph(doc, line)

            # Insert all missing figures up to the largest referenced number.
            # This guarantees the document image order stays 图1, 图2, 图3...
            refs = [int(match.group(1)) for match in FIG_REF_RE.finditer(line)]
            if refs:
                _insert_figures_through(max(refs))

    # Any remaining figures not referenced in text → append at end
    if figures:
        _set_heading(doc, "附录：数据图表", level=1)
        _insert_figures_through(max(figures))

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    doc.save(filepath)
