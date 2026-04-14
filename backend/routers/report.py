"""Report API router.

Exposes weekly, monthly, and custom-range report endpoints in both JSON,
HTML, and Excel formats.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import os
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response, FileResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import GeneratedReport
from services.report_service import ReportService
from services.ai_report import generate_ai_analysis
from services.chart_service import generate_all_charts
from services.gemini_image_service import generate_report_images
from services.docx_service import generate_docx_report
from services.report_figures import build_figure_manifest

router = APIRouter(prefix="/api/report", tags=["报告生成"])

_service = ReportService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_chart_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="chart")
_REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
os.makedirs(_REPORTS_DIR, exist_ok=True)

async def _gather_all(summary: dict) -> tuple[str, dict, dict, list[dict]]:
    """Generate charts/images first, then AI analysis from the final figure order.

    Returns:
        (ai_text, charts_dict, ai_images_dict, figure_manifest)
    """
    loop = asyncio.get_event_loop()
    chart_task = loop.run_in_executor(_chart_executor, generate_all_charts, summary)
    img_task   = asyncio.ensure_future(generate_report_images(summary))
    charts, ai_images = await asyncio.gather(chart_task, img_task)
    figure_manifest = build_figure_manifest(summary, charts, ai_images)
    ai_text = await generate_ai_analysis(summary, figure_manifest=figure_manifest)
    return ai_text, charts, ai_images, figure_manifest


def _parse_date(value: str, param_name: str) -> date:
    """Parse a YYYY-MM-DD string and raise HTTP 400 on failure."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format for '{param_name}'. Expected YYYY-MM-DD.",
        )


# ---------------------------------------------------------------------------
# JSON summary endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/weekly",
    summary="周报 — JSON 数据",
    response_description="最近 7 天聚合统计数据",
)
async def get_weekly_summary(
    end: str | None = Query(
        default=None,
        description="统计截止日期，格式 YYYY-MM-DD，默认今天",
    ),
    db: AsyncSession = Depends(get_db),
):
    end_date = _parse_date(end, "end") if end else None
    summary = await _service.get_week_summary(db, end_date=end_date)
    return {"status": "ok", "data": summary}


@router.get(
    "/monthly",
    summary="月报 — JSON 数据",
    response_description="最近 30 天聚合统计数据",
)
async def get_monthly_summary(
    end: str | None = Query(
        default=None,
        description="统计截止日期，格式 YYYY-MM-DD，默认今天",
    ),
    db: AsyncSession = Depends(get_db),
):
    end_date = _parse_date(end, "end") if end else None
    summary = await _service.get_month_summary(db, end_date=end_date)
    return {"status": "ok", "data": summary}


@router.get(
    "/custom",
    summary="自定义时间段报告 — JSON 数据",
    response_description="指定日期范围内聚合统计数据",
)
async def get_custom_summary(
    start: str = Query(..., description="起始日期，格式 YYYY-MM-DD"),
    end: str = Query(..., description="截止日期，格式 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    start_date = _parse_date(start, "start")
    end_date = _parse_date(end, "end")
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="'start' must not be later than 'end'.",
        )
    summary = await _service.get_custom_summary(db, start_date, end_date)
    return {"status": "ok", "data": summary}


# ---------------------------------------------------------------------------
# HTML report endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/weekly/html",
    summary="周报 — HTML 文件下载",
    response_class=HTMLResponse,
)
async def get_weekly_html(
    end: str | None = Query(default=None, description="截止日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    end_date = _parse_date(end, "end") if end else None
    summary = await _service.get_week_summary(db, end_date=end_date)
    ai_text, charts, ai_images, figure_manifest = await _gather_all(summary)
    html_content = ReportService.generate_html_report(
        summary,
        ai_analysis=ai_text,
        charts=charts,
        ai_images=ai_images,
        figure_manifest=figure_manifest,
    )
    filename = f"weekly_report_{summary['period']['start']}_{summary['period']['end']}.html"
    return Response(
        content=html_content,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.get(
    "/monthly/html",
    summary="月报 — HTML 文件下载",
    response_class=HTMLResponse,
)
async def get_monthly_html(
    end: str | None = Query(default=None, description="截止日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    end_date = _parse_date(end, "end") if end else None
    summary = await _service.get_month_summary(db, end_date=end_date)
    ai_text, charts, ai_images, figure_manifest = await _gather_all(summary)
    html_content = ReportService.generate_html_report(
        summary,
        ai_analysis=ai_text,
        charts=charts,
        ai_images=ai_images,
        figure_manifest=figure_manifest,
    )
    filename = f"monthly_report_{summary['period']['start']}_{summary['period']['end']}.html"
    return Response(
        content=html_content,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


# ---------------------------------------------------------------------------
# AI analysis endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/ai-analysis",
    summary="AI智能分析 — 周报 JSON",
)
async def get_ai_analysis(
    end: str | None = Query(default=None, description="截止日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """调用 DeepSeek API 对最近7天数据进行智能分析，返回分析文本。"""
    end_date = _parse_date(end, "end") if end else None
    summary = await _service.get_week_summary(db, end_date=end_date)
    ai_text = await generate_ai_analysis(summary)
    return {"status": "ok", "data": {"analysis": ai_text, "period": summary["period"]}}


# ---------------------------------------------------------------------------
# Report Management Endpoints
# ---------------------------------------------------------------------------

@router.get("/list", summary="获取已生成文章列表")
async def list_reports(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedReport).order_by(GeneratedReport.created_at.desc()))
    records = result.scalars().all()
    return {"status": "ok", "data": [
        {
            "id": r.id,
            "title": r.title,
            "report_type": r.report_type,
            "period_start": r.period_start,
            "period_end": r.period_end,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "has_html": bool(r.html_path),
            "has_docx": bool(r.docx_path),
        } for r in records
    ]}

@router.post("/generate", summary="后台生成指定时间段的文章")
async def generate_managed_report(
    report_type: str = Query(..., description="daily, weekly, monthly"),
    end: str | None = Query(default=None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db)
):
    end_date = _parse_date(end, "end") if end else date.today()
    if report_type == "daily":
        start_date = end_date
    elif report_type == "weekly":
        start_date = end_date - timedelta(days=6)
    elif report_type == "monthly":
        start_date = end_date - timedelta(days=29)
    else:
        raise HTTPException(400, "Unknown report_type. Use daily, weekly, or monthly.")
        
    summary = await _service.get_custom_summary(db, start_date, end_date)
    ai_text, charts, ai_images, figure_manifest = await _gather_all(summary)
    
    # 1. HTML
    html_content = ReportService.generate_html_report(
        summary,
        ai_analysis=ai_text,
        charts=charts,
        ai_images=ai_images,
        figure_manifest=figure_manifest,
    )
    
    report_id = str(uuid.uuid4())[:8]
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    type_name = {"daily": "日报", "weekly": "周报", "monthly": "月报"}.get(report_type, "报告")
    title = f"三亚市天涯区生态监测{type_name} ({start_str}-{end_str})"
    
    html_path = os.path.join(_REPORTS_DIR, f"{report_id}.html")
    docx_path = os.path.join(_REPORTS_DIR, f"{report_id}.docx")
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # 2. DOCX
    generate_docx_report(
        summary,
        ai_text,
        charts,
        ai_images,
        docx_path,
        figure_manifest=figure_manifest,
    )
    
    # Save to DB
    new_report = GeneratedReport(
        report_type=report_type,
        period_start=start_date.strftime("%Y-%m-%d"),
        period_end=end_date.strftime("%Y-%m-%d"),
        title=title,
        html_path=html_path,
        docx_path=docx_path
    )
    db.add(new_report)
    await db.commit()
    
    return {"status": "ok", "message": "Report generated successfully."}

@router.delete("/{report_id}", summary="删除文章")
async def delete_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
        
    if report.html_path and os.path.exists(report.html_path):
        os.remove(report.html_path)
    if report.docx_path and os.path.exists(report.docx_path):
        os.remove(report.docx_path)
        
    await db.delete(report)
    await db.commit()
    return {"status": "ok"}

@router.get("/download/{report_id}/{format}", summary="下载已生成文章")
async def download_report(report_id: int, format: str = "html", db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
        
    if format == "html" and report.html_path:
        filename = f"{report.title}.html"
        return FileResponse(report.html_path, filename=filename, media_type="text/html")
    elif format == "docx" and report.docx_path:
        filename = f"{report.title}.docx"
        return FileResponse(
            report.docx_path, 
            filename=filename, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    else:
        raise HTTPException(400, "Format not supported or file missing")
