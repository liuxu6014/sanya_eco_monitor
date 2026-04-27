"""
全量历史数据回填脚本 - 按天分块拉取虫情与孢子数据，避免单次请求数据过大。

用法:
    cd backend
    uv run python backfill_full.py --days 90        # 最近90天（默认）
    uv run python backfill_full.py --days 180 --dry-run  # 演习模式，只打印时间段
"""
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database import engine, init_db
from collectors.base import get_token
from collectors.insect import (
    _extract_records, _parse_collection_time, _parse_species,
    _extract_image_url, _existing_collection_times
)
from models import (
    InsectRecord, SporeRecord
)
from config import settings
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backfill")


def _make_range(start: datetime, end: datetime) -> str:
    fmt = "%Y-%m-%d %H:%M:%S"
    return f"{start.strftime(fmt)},{end.strftime(fmt)}"


async def sensor_get_range(path: str, code: str, start: datetime, end: datetime) -> dict:
    token = await get_token()
    time_range = _make_range(start, end)
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        resp = await client.get(
            f"{settings.SENSOR_BASE_URL}{path}",
            params={"code": code, "collectionTime": time_range},
            headers={"Authorization": token},
        )
        resp.raise_for_status()
        return resp.json()


async def platform_get_range(path: str, code: str, start: datetime, end: datetime) -> dict:
    token = await get_token()
    time_range = _make_range(start, end)
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        resp = await client.get(
            f"{settings.PLATFORM_BASE_URL}{path}",
            params={"code": code, "collectionTime": time_range},
            headers={"Authorization": token},
        )
        resp.raise_for_status()
        return resp.json()


async def backfill_insect_like(db: AsyncSession, code: str, model,
                                 task: str, start_dt: datetime, end_dt: datetime,
                                 dry_run: bool):
    """拉取虫情/孢子历史数据，按天分块。"""
    total = 0
    chunk_start = start_dt
    while chunk_start < end_dt:
        chunk_end = min(chunk_start + timedelta(days=1), end_dt)
        if dry_run:
            logger.info(f"[DRY] {task} [{code}] {_make_range(chunk_start, chunk_end)}")
            chunk_start = chunk_end
            continue
        try:
            data = await platform_get_range(
                "/http/monitor/getBugWarmByCode", code, chunk_start, chunk_end
            )
            records_data = _extract_records(data)
            parsed = [(item, t) for item in records_data
                      if (t := _parse_collection_time(item)) is not None]

            existing = await _existing_collection_times(
                db, model, code, [t for _, t in parsed]
            )

            saved = 0
            for item, col_time in parsed:
                if col_time in existing:
                    continue
                try:
                    if model == InsectRecord:
                        species = _parse_species(item.get("style") or item.get("bugList") or [])
                        total_count = sum(species.values()) or int(
                            item.get("totalCount") or item.get("total") or 0
                        )
                        db.add(InsectRecord(
                            device_code=code,
                            collection_time=col_time,
                            total_count=total_count,
                            species_data=species,
                            image_url=_extract_image_url(item),
                            raw_data=item,
                        ))
                    else:  # SporeRecord
                        spore_data = _parse_species(item.get("style") or item.get("sporeList") or [])
                        total_count = sum(spore_data.values()) or int(
                            item.get("totalCount") or item.get("total") or 0
                        )
                        db.add(SporeRecord(
                            device_code=code,
                            collection_time=col_time,
                            total_count=total_count,
                            spore_data=spore_data,
                            image_url=_extract_image_url(item),
                            raw_data=item,
                        ))
                    saved += 1
                except Exception as ex:
                    logger.warning(f"  parse error: {ex}")

            await db.commit()
            logger.info(f"  {task} [{code}] {chunk_start.date()} → saved {saved}/{len(parsed)}")
            total += saved
        except Exception as e:
            logger.warning(f"  {task} [{code}] {chunk_start.date()} ERROR: {e}")
        chunk_start = chunk_end
    return total


async def main():
    parser = argparse.ArgumentParser(description="全量历史数据回填")
    parser.add_argument("--days", type=int, default=90, help="回溯天数（默认90天）")
    parser.add_argument("--dry-run", action="store_true", help="演习模式，不写入数据库")
    args = parser.parse_args()

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=args.days)

    logger.info(f"=== 回填范围: {start_dt.date()} → {end_dt.date()} ({args.days}天) ===")
    if args.dry_run:
        logger.info("！！！演习模式（dry-run），不写入数据库！！！")

    if not args.dry_run:
        await init_db()

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        results = {}

        logger.info("\n--- [1/2] 虫情测报灯 ---")
        results["insect"] = await backfill_insect_like(
            db, settings.INSECT_CODE, InsectRecord, "insect", start_dt, end_dt, args.dry_run
        )

        logger.info("\n--- [2/2] 孢子捕捉仪 ---")
        results["spore"] = await backfill_insect_like(
            db, settings.SPORE_CODE, SporeRecord, "spore", start_dt, end_dt, args.dry_run
        )

    logger.info("\n=== 回填完成 ===")
    for k, v in results.items():
        logger.info(f"  {k}: {v} records {'(dry-run)' if args.dry_run else 'saved'}")


if __name__ == "__main__":
    asyncio.run(main())
