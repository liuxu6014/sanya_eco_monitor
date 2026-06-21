"""APScheduler定时采集任务."""
import logging
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from database import AsyncSessionLocal
from models import GeneratedReport
from collectors.insect import collect_insect, collect_spore
from collectors.runoff import collect_runoff, collect_rain_gauges
from collectors.water_quality import collect_water_quality
from config import settings

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def _run_all_collectors():
    logger.info("=== Starting scheduled data collection ===")
    async with AsyncSessionLocal() as db:
        await collect_insect(db)
        await collect_spore(db)
        await collect_runoff(db)
        await collect_rain_gauges(db)
        await collect_water_quality(db)
    logger.info("=== Data collection complete ===")


async def _record_device_status():
    """每轮按"最新数据时间戳是否陈旧"判活，把在线→离线翻转写入 device_status_events。

    不依赖 HTTP 探测——平台接口即使设备停报通常仍回 200，会误判在线；
    以数据时间戳新鲜度为准，与空档反推统计同源。
    """
    from services.device_uptime import compute_current_statuses, record_status_snapshot

    try:
        async with AsyncSessionLocal() as db:
            statuses = await compute_current_statuses(db)
            await record_status_snapshot(db, statuses)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Device status snapshot failed: %s", exc)


async def _clean_old_reports():
    logger.info("=== Starting old reports cleanup ===")
    async with AsyncSessionLocal() as db:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        result = await db.execute(select(GeneratedReport).where(GeneratedReport.created_at < thirty_days_ago))
        old_reports = result.scalars().all()
        for report in old_reports:
            try:
                if report.html_path and os.path.exists(report.html_path):
                    os.remove(report.html_path)
                if report.docx_path and os.path.exists(report.docx_path):
                    os.remove(report.docx_path)
                await db.delete(report)
                logger.info(f"Deleted old report (ID: {report.id}, Date: {report.created_at})")
            except Exception as e:
                logger.error(f"Failed to delete old report {report.id}: {e}")
        
        await db.commit()
    logger.info("=== Old reports cleanup complete ===")


def setup_scheduler():
    scheduler.add_job(
        _run_all_collectors,
        trigger=IntervalTrigger(minutes=settings.COLLECT_INTERVAL_MINUTES),
        id="collect_all",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )
    
    # 设备状态采样：记录在线→离线翻转，用于设备运维统计
    scheduler.add_job(
        _record_device_status,
        trigger=IntervalTrigger(minutes=settings.COLLECT_INTERVAL_MINUTES),
        id="record_device_status",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    # 添加每天清理过期报告的任务
    scheduler.add_job(
        _clean_old_reports,
        trigger=IntervalTrigger(days=1),
        id="cleanup_reports",
        replace_existing=True,
        max_instances=1,
    )
    
    return scheduler
