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

Appendix (at end):
  附录一 虫情测报灯采集实景图像  (downloaded from InsectRecord.image_url)
  附录二 孢子捕捉仪采集实景图像  (downloaded from SporeRecord.image_url)
"""

import io
import base64
import os
import re
import logging
from collections import defaultdict

import httpx
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
from services.report_figures import (
    build_figure_manifest,
    build_figure_map as build_shared_figure_map,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _download_image(url: str, timeout: int = 15) -> bytes | None:
    """Download image bytes from a URL; return None on failure."""
    try:
        with httpx.Client(verify=False, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception as exc:
        logger.warning("Failed to download image %s: %s", url, exc)
        return None


def _insert_url_image(doc, url: str, caption: str, width_inches: float = 5.5):
    """Download image from URL and insert into the document. Handles relative URLs."""
    # Handle relative URLs if they happen to be stored as such
    if url.startswith('/'):
        # For local downloads, we might need a base URL.
        # However, many IoT URLs are absolute. If we find relative ones, we assume they are local.
        # For now, let's assume absolute or try to handle standard local paths.
        pass

    img_bytes = _download_image(url)
    if not img_bytes:
        # Insert placeholder text instead
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"[图片加载失败: {caption}]")
        _set_cjk_font(run, bold=False)
        run.font.size = Pt(9)
        return

    try:
        pic_para = doc.add_paragraph()
        pic_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = pic_para.add_run()
        run.add_picture(io.BytesIO(img_bytes), width=Inches(width_inches))
    except Exception as exc:
        logger.warning("Failed to insert image %s: %s", caption, exc)
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
# Appendix: device capture images
# ---------------------------------------------------------------------------

def _append_device_image_section(doc, summary: dict):
    """
    Append an appendix of actual on-device capture photos from insect traps
    and spore collectors. Groups by device code, sorted by time.

    Structure:
      附录：设备采集实景图像
        一、虫情测报灯采集图像（设备编号: XXXXXX）
           [图片] 采集时间: YYYY-MM-DD HH:MM
           ...
        二、孢子捕捉仪采集图像（设备编号: XXXXXX）
           ...
    """
    insect_images: list[dict] = (summary.get("insect") or {}).get("capture_images") or []
    spore_images: list[dict] = (summary.get("spore") or {}).get("capture_images") or []

    if not insect_images and not spore_images:
        return  # Nothing to add

    doc.add_page_break()
    _set_heading(doc, "附录：设备采集实景图像", level=1)
    p = doc.add_paragraph()
    note_run = p.add_run("以下图像均来自各监测设备在报告周期内自动采集的实时照片，按设备分组、时间顺序排列。")
    _set_cjk_font(note_run, bold=False)
    note_run.font.size = Pt(10)

    # ---- 虫情测报灯 ----
    if insect_images:
        # Group by device_code
        by_device: dict[str, list[dict]] = defaultdict(list)
        for img in insect_images:
            by_device[img["device_code"]].append(img)

        _set_heading(doc, "一、虫情测报灯采集图像", level=2)
        for device_code, imgs in by_device.items():
            _set_heading(doc, f"设备编号：{device_code}", level=3)
            for idx, img in enumerate(imgs, 1):
                caption = f"图 虫情捕获实景 {idx}   采集时间：{img['time']}"
                _insert_url_image(doc, img["url"], caption, width_inches=5.0)

    # ---- 孢子捕捉仪 ----
    if spore_images:
        by_device_s: dict[str, list[dict]] = defaultdict(list)
        for img in spore_images:
            by_device_s[img["device_code"]].append(img)

        _set_heading(doc, "二、孢子捕捉仪采集图像", level=2)
        for device_code, imgs in by_device_s.items():
            _set_heading(doc, f"设备编号：{device_code}", level=3)
            for idx, img in enumerate(imgs, 1):
                caption = f"图 孢子采集实景 {idx}   采集时间：{img['time']}"
                _insert_url_image(doc, img["url"], caption, width_inches=5.0)


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
    """Generate a Word document with images inserted inline at （见图N） positions,
    followed by a device capture image appendix."""
    doc = Document()

    # Global styles
    for style_name in ['Normal', 'Heading 1', 'Heading 2', 'Heading 3', 'Title']:
        if style_name in doc.styles:
            s = doc.styles[style_name]
            s.font.name = 'Microsoft YaHei'
            if s.element.rPr is not None:
                s.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')

    # Footer with page numbers (Page X of Y)
    section = doc.sections[0]
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # "Page "
    run = fp.add_run("第 ")
    _set_cjk_font(run)
    
    # Current Page field
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText1 = OxmlElement('w:instrText')
    instrText1.set(qn('xml:space'), 'preserve')
    instrText1.text = "PAGE"
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')
    
    fp._p.append(fldChar1)
    fp._p.append(instrText1)
    fp._p.append(fldChar2)
    
    # " / "
    run = fp.add_run(" / ")
    _set_cjk_font(run)
    
    # Total Pages field
    fldChar3 = OxmlElement('w:fldChar')
    fldChar3.set(qn('w:fldCharType'), 'begin')
    instrText2 = OxmlElement('w:instrText')
    instrText2.set(qn('xml:space'), 'preserve')
    instrText2.text = "NUMPAGES"
    fldChar4 = OxmlElement('w:fldChar')
    fldChar4.set(qn('w:fldCharType'), 'end')
    
    fp._p.append(fldChar3)
    fp._p.append(instrText2)
    fp._p.append(fldChar4)
    
    run = fp.add_run(" 页")
    _set_cjk_font(run)

    # Title
    period = summary.get("period", {})
    t_start = period.get("start", "")
    t_end = period.get("end", "")
    _set_heading(doc, "橡胶林近自然化改造生态效益评估报告", level=0)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("三亚市天涯区橡胶林近自然化改造和农田提升监测平台")
    _set_cjk_font(r, bold=True)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"统计周期：{t_start} 至 {t_end}")
    _set_cjk_font(r)

    # Cover image
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

    FIG_REF_RE = re.compile(r'[（(](?:见)?图(\d+)[）)]')
    next_expected_fig = 1

    def _insert_figures_through(target_fig: int) -> None:
        nonlocal next_expected_fig
        while next_expected_fig <= target_fig:
            if next_expected_fig in figures:
                b64, caption = figures[next_expected_fig]
                _insert_figure(doc, b64, caption)
                figures.pop(next_expected_fig, None)
            next_expected_fig += 1

    # Render AI analysis
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

            # Check for figure references and insert figures immediately after the paragraph
            refs = sorted([int(match.group(1)) for match in FIG_REF_RE.finditer(line)])
            if refs:
                # Insert all figures up to the highest one mentioned in this line
                _insert_figures_through(max(refs))

    # Any remaining AI/chart figures → standard appendix
    if figures:
        _set_heading(doc, "附录：数据图表", level=1)
        _insert_figures_through(max(figures))

    # Device capture image appendix (downloads from CDN URLs)
    _append_device_image_section(doc, summary)

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    doc.save(filepath)
