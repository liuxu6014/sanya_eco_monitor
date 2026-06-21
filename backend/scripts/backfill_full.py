"""
Full historical data backfill.

The script backfills:
- insect and spore records from the ZHNL platform, chunked by day
- rainfall, runoff and water-quality records from the WHXPH history API

Examples:
    python scripts/backfill_full.py --days 90
    python scripts/backfill_full.py --days 365 --only whxph
    python scripts/backfill_full.py --dry-run --days 1 --only water
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collectors.base import get_token
from collectors.insect import (
    _existing_collection_times,
    _extract_image_url,
    _extract_records,
    _parse_collection_time,
    _parse_species,
)
from collectors.runoff import _extract_fields as _extract_runoff_fields
from collectors.runoff import _parse_float
from collectors.water_quality import WQ_FIELD_MAP
from config import settings
from database import engine, init_db
from models import InsectRecord, RainfallRecord, RunoffRecord, SporeRecord, WaterQualityRecord


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill")


def _make_range(start: datetime, end: datetime) -> str:
    fmt = "%Y-%m-%d %H:%M:%S"
    return f"{start.strftime(fmt)},{end.strftime(fmt)}"


async def platform_get_range(path: str, code: str, start: datetime, end: datetime) -> dict:
    token = await get_token()
    time_range = _make_range(start, end)
    async with httpx.AsyncClient(verify=settings.HTTP_TLS_VERIFY, timeout=30) as client:
        resp = await client.get(
            f"{settings.PLATFORM_BASE_URL}{path}",
            params={"code": code, "collectionTime": time_range},
            headers={"Authorization": token},
        )
        resp.raise_for_status()
        return resp.json()


async def whxph_get(path: str, params: dict | None = None) -> dict | list:
    base_url = settings.WHXPH_BASE_URL.rstrip("/")
    async with httpx.AsyncClient(verify=settings.HTTP_TLS_VERIFY, timeout=60) as client:
        resp = await client.get(
            f"{base_url}{path}",
            params=params or {},
            headers={"accept": "*/*"},
        )
        resp.raise_for_status()
        return resp.json()


def _configured_codes(raw: str | None, fallback: str = "") -> list[str]:
    source = raw or fallback
    return [code.strip() for code in source.split(",") if code.strip()]


def _parse_whxph_collection_time(item: dict) -> datetime | None:
    value = item.get("dataTime") or item.get("datetime")
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _whxph_history_row_to_latest_shape(row: dict, code: str, element_map: dict[str, dict]) -> dict:
    ele_lists = []
    for key, meta in element_map.items():
        if key not in row:
            continue
        ele_lists.append(
            {
                "eKey": key,
                "eName": meta.get("eName") or key,
                "eUnit": meta.get("eUnit") or "",
                "eNum": meta.get("eNum"),
                "eValue": str(row.get(key)),
            }
        )

    return {
        "datetime": row.get("dataTime") or row.get("datetime"),
        "deviceId": row.get("facId") or row.get("deviceId") or code,
        "name": row.get("facName") or row.get("name") or code,
        "eleLists": ele_lists,
        "rawHistoryRow": row,
    }


async def _whxph_element_map(code: str) -> dict[str, dict]:
    latest = await whxph_get(f"/data-n/{code}")
    if not isinstance(latest, dict):
        return {}
    return {
        item.get("eKey"): item
        for item in latest.get("eleLists", [])
        if item.get("eKey")
    }


def _extract_whxph_rows(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "rows", "records", "list"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _extract_whxph_rows(value)
            if nested:
                return nested
    return []


async def _existing_times(
    db: AsyncSession,
    model,
    code: str,
    times: list[datetime],
) -> set[datetime]:
    if not times:
        return set()
    result = await db.execute(
        select(model.collection_time).where(
            model.device_code == code,
            model.collection_time.in_(times),
        )
    )
    return set(result.scalars().all())


async def _delete_range(
    db: AsyncSession,
    model,
    codes: list[str],
    start_dt: datetime,
    end_dt: datetime,
) -> int:
    if not codes:
        return 0
    result = await db.execute(
        delete(model).where(
            model.device_code.in_(codes),
            model.collection_time >= start_dt,
            model.collection_time <= end_dt,
        )
    )
    await db.commit()
    return int(result.rowcount or 0)


async def _iter_whxph_history(
    code: str,
    start_dt: datetime,
    end_dt: datetime,
    interval: int,
    page_size: int,
):
    page = 1
    while True:
        payload = await whxph_get(
            f"/datas/{code}",
            params={
                "pageNum": page,
                "pageSize": page_size,
                "startTime": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "endTime": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "deviceId": code,
                "interval": interval,
                "sort": "ASC",
            },
        )
        rows = _extract_whxph_rows(payload)
        if not rows:
            break
        yield page, rows
        page += 1


def _water_quality_fields(ele_lists: list[dict]) -> dict:
    fields: dict[str, float | None] = {}
    for item in ele_lists:
        field_name = WQ_FIELD_MAP.get(item.get("eName", ""))
        if field_name and field_name not in fields:
            fields[field_name] = _parse_float(item.get("eValue"))
    return fields


async def backfill_insect_like(
    db: AsyncSession,
    code: str,
    model,
    task: str,
    start_dt: datetime,
    end_dt: datetime,
    dry_run: bool,
):
    """Backfill insect/spore history, chunked by day."""
    total = 0
    chunk_start = start_dt
    while chunk_start < end_dt:
        chunk_end = min(chunk_start + timedelta(days=1), end_dt)
        if dry_run:
            logger.info("[DRY] %s [%s] %s", task, code, _make_range(chunk_start, chunk_end))
            chunk_start = chunk_end
            continue

        try:
            data = await platform_get_range(
                "/http/monitor/getBugWarmByCode", code, chunk_start, chunk_end
            )
            records_data = _extract_records(data)
            parsed = [
                (item, col_time)
                for item in records_data
                if (col_time := _parse_collection_time(item)) is not None
            ]

            existing = await _existing_collection_times(
                db, model, code, [col_time for _, col_time in parsed]
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
                        db.add(
                            InsectRecord(
                                device_code=code,
                                collection_time=col_time,
                                total_count=total_count,
                                species_data=species,
                                image_url=_extract_image_url(item),
                                raw_data=item,
                            )
                        )
                    else:
                        spore_data = _parse_species(
                            item.get("style") or item.get("sporeList") or []
                        )
                        total_count = sum(spore_data.values()) or int(
                            item.get("totalCount") or item.get("total") or 0
                        )
                        db.add(
                            SporeRecord(
                                device_code=code,
                                collection_time=col_time,
                                total_count=total_count,
                                spore_data=spore_data,
                                image_url=_extract_image_url(item),
                                raw_data=item,
                            )
                        )
                    saved += 1
                except Exception as exc:
                    logger.warning("  %s [%s] parse error: %s", task, code, exc)

            await db.commit()
            logger.info(
                "  %s [%s] %s -> saved %s/%s",
                task,
                code,
                chunk_start.date(),
                saved,
                len(parsed),
            )
            total += saved
        except Exception as exc:
            await db.rollback()
            logger.warning("  %s [%s] %s ERROR: %s", task, code, chunk_start.date(), exc)
        chunk_start = chunk_end
    return total


async def backfill_whxph_device(
    db: AsyncSession,
    code: str,
    model,
    task: str,
    start_dt: datetime,
    end_dt: datetime,
    interval: int,
    page_size: int,
    dry_run: bool,
):
    if dry_run:
        logger.info(
            "[DRY] %s [%s] /datas/%s %s -> %s interval=%s page_size=%s",
            task,
            code,
            code,
            start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            interval,
            page_size,
        )
        return 0

    total = 0
    try:
        element_map = await _whxph_element_map(code)
        if not element_map:
            logger.warning("  %s [%s] no element metadata, skipped", task, code)
            return 0

        async for page, rows in _iter_whxph_history(code, start_dt, end_dt, interval, page_size):
            parsed = [
                (row, col_time)
                for row in rows
                if (col_time := _parse_whxph_collection_time(row)) is not None
            ]
            existing = await _existing_times(
                db,
                model,
                code,
                [col_time for _, col_time in parsed],
            )

            saved = 0
            for row, col_time in parsed:
                if col_time in existing:
                    continue

                shaped = _whxph_history_row_to_latest_shape(row, code, element_map)
                ele_lists = shaped.get("eleLists") or []
                if model == RainfallRecord:
                    rainfall = _extract_runoff_fields(ele_lists).get("rainfall")
                    db.add(
                        RainfallRecord(
                            device_code=code,
                            collection_time=col_time,
                            rainfall=rainfall,
                            raw_data=shaped,
                        )
                    )
                elif model == RunoffRecord:
                    db.add(
                        RunoffRecord(
                            device_code=code,
                            collection_time=col_time,
                            raw_data=shaped,
                            **_extract_runoff_fields(ele_lists),
                        )
                    )
                elif model == WaterQualityRecord:
                    db.add(
                        WaterQualityRecord(
                            device_code=code,
                            collection_time=col_time,
                            raw_data=shaped,
                            **_water_quality_fields(ele_lists),
                        )
                    )
                else:
                    raise ValueError(f"Unsupported WHXPH model: {model}")
                saved += 1

            await db.commit()
            total += saved
            logger.info(
                "  %s [%s] page %s -> saved %s/%s",
                task,
                code,
                page,
                saved,
                len(parsed),
            )
    except Exception as exc:
        await db.rollback()
        logger.warning("  %s [%s] ERROR: %s", task, code, exc)
    return total


async def main():
    parser = argparse.ArgumentParser(description="Full historical data backfill")
    parser.add_argument("--days", type=int, default=90, help="Days to backfill, default 90")
    parser.add_argument("--dry-run", action="store_true", help="Print ranges without writing")
    parser.add_argument(
        "--only",
        choices=("all", "insect", "spore", "rainfall", "runoff", "water", "whxph"),
        default="all",
        help="Limit backfill scope. whxph means rainfall + runoff + water.",
    )
    parser.add_argument(
        "--whxph-interval",
        type=int,
        default=1,
        help="WHXPH history interval in minutes. 1 is the finest full backfill.",
    )
    parser.add_argument(
        "--whxph-page-size",
        type=int,
        default=1000,
        help="WHXPH history page size.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing records in the selected date range before backfilling.",
    )
    args = parser.parse_args()

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=args.days)

    logger.info(
        "=== backfill range: %s -> %s (%s days), scope=%s ===",
        start_dt.date(),
        end_dt.date(),
        args.days,
        args.only,
    )
    if args.dry_run:
        logger.info("dry-run mode: database will not be changed")

    if not args.dry_run:
        await init_db()

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        results: dict[str, int] = {}
        insect_codes = _configured_codes(settings.INSECT_CODE)
        spore_codes = _configured_codes(settings.SPORE_CODE)
        rain_codes = _configured_codes(
            settings.RAIN_GAUGE_CODES,
            "16132920,16132921,16132922",
        )
        runoff_codes = _configured_codes(settings.RUNOFF_CODES)
        water_codes = _configured_codes(settings.WATER_QUALITY_CODE)

        if args.replace:
            if args.dry_run:
                logger.info("replace requested in dry-run mode: no rows will be deleted")
            else:
                logger.warning(
                    "replace mode: deleting selected records from %s to %s before backfill",
                    start_dt,
                    end_dt,
                )
                if args.only in {"all", "insect"}:
                    deleted = await _delete_range(db, InsectRecord, insect_codes, start_dt, end_dt)
                    logger.warning("  deleted insect rows: %s", deleted)
                if args.only in {"all", "spore"}:
                    deleted = await _delete_range(db, SporeRecord, spore_codes, start_dt, end_dt)
                    logger.warning("  deleted spore rows: %s", deleted)
                if args.only in {"all", "rainfall", "whxph"}:
                    deleted = await _delete_range(db, RainfallRecord, rain_codes, start_dt, end_dt)
                    logger.warning("  deleted rainfall rows: %s", deleted)
                if args.only in {"all", "runoff", "whxph"}:
                    deleted = await _delete_range(db, RunoffRecord, runoff_codes, start_dt, end_dt)
                    logger.warning("  deleted runoff rows: %s", deleted)
                if args.only in {"all", "water", "whxph"}:
                    deleted = await _delete_range(db, WaterQualityRecord, water_codes, start_dt, end_dt)
                    logger.warning("  deleted water rows: %s", deleted)

        if args.only in {"all", "insect"}:
            logger.info("\n--- insect history ---")
            results["insect"] = await backfill_insect_like(
                db,
                settings.INSECT_CODE,
                InsectRecord,
                "insect",
                start_dt,
                end_dt,
                args.dry_run,
            )

        if args.only in {"all", "spore"}:
            logger.info("\n--- spore history ---")
            results["spore"] = await backfill_insect_like(
                db,
                settings.SPORE_CODE,
                SporeRecord,
                "spore",
                start_dt,
                end_dt,
                args.dry_run,
            )

        if args.only in {"all", "rainfall", "whxph"}:
            logger.info("\n--- rainfall history (WHXPH) ---")
            results["rainfall"] = 0
            for code in rain_codes:
                results["rainfall"] += await backfill_whxph_device(
                    db,
                    code,
                    RainfallRecord,
                    "rainfall",
                    start_dt,
                    end_dt,
                    args.whxph_interval,
                    args.whxph_page_size,
                    args.dry_run,
                )

        if args.only in {"all", "runoff", "whxph"}:
            logger.info("\n--- runoff history (WHXPH) ---")
            results["runoff"] = 0
            for code in runoff_codes:
                results["runoff"] += await backfill_whxph_device(
                    db,
                    code,
                    RunoffRecord,
                    "runoff",
                    start_dt,
                    end_dt,
                    args.whxph_interval,
                    args.whxph_page_size,
                    args.dry_run,
                )

        if args.only in {"all", "water", "whxph"}:
            logger.info("\n--- water-quality history (WHXPH) ---")
            results["water"] = 0
            for code in water_codes:
                results["water"] += await backfill_whxph_device(
                    db,
                    code,
                    WaterQualityRecord,
                    "water",
                    start_dt,
                    end_dt,
                    args.whxph_interval,
                    args.whxph_page_size,
                    args.dry_run,
                )

    logger.info("\n=== backfill complete ===")
    for key, value in results.items():
        logger.info("  %s: %s records %s", key, value, "(dry-run)" if args.dry_run else "saved")


if __name__ == "__main__":
    asyncio.run(main())
