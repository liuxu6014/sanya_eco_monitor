"""Report API router.

Exposes weekly, monthly, and custom-range report endpoints in both JSON,
HTML, and Excel formats.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import os
import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response, FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import auth_role_from_cookie
from config import settings
from database import AsyncSessionLocal, get_db
from models import GeneratedReport
from services.report_service import ReportService
from services.ai_report import generate_ai_analysis
from services.chart_service import generate_all_charts
from services.gemini_image_service import generate_report_images
from services.docx_service import generate_docx_report
from services.report_figures import build_figure_manifest
from time_utils import cn_now_naive

router = APIRouter(prefix="/api/report", tags=["报告生成"])
logger = logging.getLogger(__name__)

_service = ReportService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_chart_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="chart")
_REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
os.makedirs(_REPORTS_DIR, exist_ok=True)


def _build_download_response(path: str | None, filename: str, media_type: str):
    if not path:
        raise HTTPException(404, "Report file is not available")
    if not os.path.exists(path):
        logger.warning("Report file missing on disk: %s", path)
        raise HTTPException(404, "Report file is missing")
    return FileResponse(path, filename=filename, media_type=media_type)


async def _gather_all(summary: dict) -> tuple[str, dict, dict, list[dict]]:
    """Generate charts/images first, then AI analysis from the final figure order.

    Returns:
        (ai_text, charts_dict, ai_images_dict, figure_manifest)
    """
    loop = asyncio.get_running_loop()
    chart_task = loop.run_in_executor(_chart_executor, generate_all_charts, summary)
    img_task = asyncio.create_task(generate_report_images(summary))
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


def _require_admin(request: Request) -> None:
    if auth_role_from_cookie(request.cookies.get(settings.AUTH_COOKIE_NAME)) != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")


def _report_dict(report: GeneratedReport) -> dict:
    review_deadline = report.created_at + timedelta(days=1)
    return {
        "id": report.id,
        "title": report.title,
        "report_type": report.report_type,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "created_at": report.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "has_html": bool(report.html_path),
        "has_docx": bool(report.docx_path),
        "status": report.status,
        "review_status": report.review_status,
        "visible_to_leader": bool(report.visible_to_leader),
        "reviewed_at": report.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if report.reviewed_at else None,
        "review_deadline": review_deadline.strftime("%Y-%m-%d %H:%M:%S"),
        "review_overdue": report.review_status != "approved" and cn_now_naive() > review_deadline,
        "task_id": report.task_id,
        "error_message": report.error_message,
    }


async def _build_and_store_report(report_db_id: int, report_type: str, start_date: date, end_date: date) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_db_id))
        report = result.scalar_one_or_none()
        if not report:
            return

        report.status = "running"
        report.error_message = None
        await db.commit()

        html_path = report.html_path
        docx_path = report.docx_path
        try:
            summary = await _service.get_custom_summary(db, start_date, end_date)
            ai_text, charts, ai_images, figure_manifest = await _gather_all(summary)
            html_content = ReportService.generate_html_report(
                summary,
                ai_analysis=ai_text,
                charts=charts,
                ai_images=ai_images,
                figure_manifest=figure_manifest,
            )

            if html_path:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

            if docx_path:
                generate_docx_report(
                    summary,
                    ai_text,
                    charts,
                    ai_images,
                    docx_path,
                    figure_manifest=figure_manifest,
                )

            report.status = "completed"
            report.review_status = "pending"
            report.visible_to_leader = False
            report.error_message = None
            await db.commit()
        except Exception as exc:
            await db.rollback()
            result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_db_id))
            report = result.scalar_one_or_none()
            if report:
                report.status = "failed"
                report.error_message = str(exc)
                await db.commit()
            logger.exception("background report generation failed: report_id=%s type=%s", report_db_id, report_type)


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
    return {
        "status": "ok",
        "data": {
            "analysis": ai_text,
            "period": summary["period"],
        },
    }


# ---------------------------------------------------------------------------
# Report Management Endpoints
# ---------------------------------------------------------------------------

@router.get("/list", summary="获取已生成文章列表")
async def list_reports(request: Request, db: AsyncSession = Depends(get_db)):
    role = auth_role_from_cookie(request.cookies.get(settings.AUTH_COOKIE_NAME))
    stmt = select(GeneratedReport)
    if role == "leader":
        stmt = stmt.where(
            GeneratedReport.status == "completed",
            GeneratedReport.review_status == "approved",
            GeneratedReport.visible_to_leader.is_(True),
        )
    result = await db.execute(stmt.order_by(GeneratedReport.created_at.desc()))
    records = result.scalars().all()
    pending_review = [r for r in records if r.status == "completed" and r.review_status != "approved"]
    overdue_review = [r for r in pending_review if cn_now_naive() > r.created_at + timedelta(days=1)]
    return {
        "status": "ok",
        "role": role,
        "review_reminder": {
            "pending": len(pending_review),
            "overdue": len(overdue_review),
        },
        "data": [_report_dict(r) for r in records],
    }

@router.post("/generate", summary="后台生成指定时间段的文章")
async def generate_managed_report(
    background_tasks: BackgroundTasks,
    request: Request,
    report_type: str = Query(..., description="daily, weekly, monthly"),
    end: str | None = Query(default=None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db)
):
    _require_admin(request)
    end_date = _parse_date(end, "end") if end else date.today()
    if report_type == "daily":
        start_date = end_date
    elif report_type == "weekly":
        start_date = end_date - timedelta(days=6)
    elif report_type == "monthly":
        start_date = end_date - timedelta(days=29)
    else:
        raise HTTPException(400, "Unknown report_type. Use daily, weekly, or monthly.")

    report_id = str(uuid.uuid4())[:8]
    html_path = os.path.join(_REPORTS_DIR, f"{report_id}.html")
    docx_path = os.path.join(_REPORTS_DIR, f"{report_id}.docx")

    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    type_name = {"daily": "日报", "weekly": "周报", "monthly": "月报"}.get(report_type, "报告")
    title = f"三亚市天涯区生态监测{type_name} ({start_str}-{end_str})"

    new_report = GeneratedReport(
        report_type=report_type,
        period_start=start_date.strftime("%Y-%m-%d"),
        period_end=end_date.strftime("%Y-%m-%d"),
        title=title,
        html_path=html_path,
        docx_path=docx_path,
        created_at=cn_now_naive(),
        status="queued",
        review_status="pending",
        visible_to_leader=False,
        task_id=report_id,
    )
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    background_tasks.add_task(_build_and_store_report, new_report.id, report_type, start_date, end_date)
    return {
        "status": "accepted",
        "message": "报告已进入后台生成队列，完成后会在列表中提示。",
        "data": _report_dict(new_report),
    }

@router.delete("/{report_id}", summary="删除文章")
async def delete_report(report_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    _require_admin(request)
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
async def download_report(
    report_id: int,
    request: Request,
    format: str = "html",
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")

    role = auth_role_from_cookie(request.cookies.get(settings.AUTH_COOKIE_NAME))
    if role == "leader" and not (
        report.status == "completed" and report.review_status == "approved" and report.visible_to_leader
    ):
        raise HTTPException(status_code=403, detail="报告尚未审核通过")
        
    if format == "html":
        filename = f"{report.title}.html"
        return _build_download_response(report.html_path, filename, "text/html")
    elif format == "docx":
        filename = f"{report.title}.docx"
        return _build_download_response(
            report.docx_path,
            filename,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    else:
        raise HTTPException(400, "Format not supported")


@router.post("/{report_id}/approve", summary="审核通过报告")
async def approve_report(report_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    _require_admin(request)
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    if report.status != "completed":
        raise HTTPException(400, "报告尚未生成完成，不能审核")
    report.review_status = "approved"
    report.visible_to_leader = True
    report.reviewed_at = cn_now_naive()
    await db.commit()
    await db.refresh(report)
    return {"status": "ok", "data": _report_dict(report)}


@router.post("/{report_id}/reject", summary="审核驳回报告")
async def reject_report(report_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    _require_admin(request)
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    report.review_status = "rejected"
    report.visible_to_leader = False
    report.reviewed_at = cn_now_naive()
    await db.commit()
    await db.refresh(report)
    return {"status": "ok", "data": _report_dict(report)}
