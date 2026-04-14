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
from collectors.sensor import collect_weather, collect_soil
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
        await collect_weather(db)
        await collect_soil(db)
        await collect_runoff(db)
        await collect_rain_gauges(db)
        await collect_water_quality(db)
    logger.info("=== Data collection complete ===")


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
    
    # 添加每天清理过期报告的任务
    scheduler.add_job(
        _clean_old_reports,
        trigger=IntervalTrigger(days=1),
        id="cleanup_reports",
        replace_existing=True,
        max_instances=1,
    )
    
    return scheduler
