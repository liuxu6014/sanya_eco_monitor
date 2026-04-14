"""Collectors for insect lamp and spore capture devices."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from collectors.base import platform_get
from config import settings
from models import CollectLog, InsectRecord, SporeRecord

logger = logging.getLogger(__name__)


def _build_time_range(hours_back: int) -> str:
    """Build the collectionTime query param for the last N hours."""
    end = datetime.now()
    start = end - timedelta(hours=hours_back)
    fmt = "%Y-%m-%d %H:%M:%S"
    return f"{start.strftime(fmt)},{end.strftime(fmt)}"


def _parse_species(raw_list: list) -> dict:
    """Parse species/style items into a normalized dict."""
    result = {}
    for item in raw_list or []:
        name = item.get("name") or item.get("bugName", "未知")
        try:
            value = int(float(item.get("value") or item.get("count") or 0))
        except (ValueError, TypeError):
            value = 0
        if name:
            result[name] = result.get(name, 0) + value
    return result


def _extract_records(data: dict) -> list[dict]:
    resp_data = data.get("data") or {}
    if isinstance(resp_data, dict) and "list" in resp_data:
        return resp_data["list"] or []
    if isinstance(resp_data, list):
        return resp_data
    return [resp_data] if resp_data else []


def _parse_collection_time(item: dict) -> datetime | None:
    col_time_str = item.get("collectionTime") or item.get("createTime", "")
    if not col_time_str:
        return None
    try:
        return datetime.strptime(col_time_str[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        logger.warning("Failed to parse collection_time: %s", col_time_str)
        return None


def _extract_image_url(item: dict) -> str | None:
    return (
        item.get("pictureUrl")
        or item.get("exhibitionPath")
        or item.get("picUrl")
        or item.get("imageUrl")
        or item.get("imgUrl")
    )


async def _existing_collection_times(
    db: AsyncSession,
    model,
    device_code: str,
    candidate_times: list[datetime],
) -> set[datetime]:
    """Fetch existing timestamps for the same device to avoid duplicate inserts."""
    if not candidate_times:
        return set()

    result = await db.execute(
        select(model.collection_time).where(
            model.device_code == device_code,
            model.collection_time.in_(candidate_times),
        )
    )
    return set(result.scalars().all())


async def collect_insect(db: AsyncSession) -> int:
    """Fetch insect trap data and store new records."""
    time_range = _build_time_range(hours_back=settings.INSECT_LOOKBACK_HOURS)
    try:
        data = await platform_get(
            "/http/monitor/getBugWarmByCode",
            params={"code": settings.INSECT_CODE, "collectionTime": time_range},
        )
    except Exception as exc:
        logger.error("collect_insect error: %s", exc)
        db.add(CollectLog(task_name="insect", status="error", message=str(exc)))
        await db.commit()
        return 0

    records_data = _extract_records(data)
    parsed_items = []
    for item in records_data:
        col_time = _parse_collection_time(item)
        if col_time is not None:
            parsed_items.append((item, col_time))

    existing_times = await _existing_collection_times(
        db, InsectRecord, settings.INSECT_CODE, [col_time for _, col_time in parsed_items]
    )

    saved = 0
    for item, col_time in parsed_items:
        if col_time in existing_times:
            continue
        try:
            species = _parse_species(item.get("style") or item.get("bugList") or [])
            total = sum(species.values()) or int(
                item.get("totalCount") or item.get("total") or item.get("value") or 0
            )

            db.add(
                InsectRecord(
                    device_code=settings.INSECT_CODE,
                    collection_time=col_time,
                    total_count=total,
                    species_data=species,
                    image_url=_extract_image_url(item),
                    raw_data=item,
                )
            )
            saved += 1
        except Exception as exc:
            logger.warning("Failed to parse insect record: %s | data=%s", exc, item)

    db.add(CollectLog(task_name="insect", status="success", records_count=saved))
    await db.commit()
    logger.info("collect_insect: saved %s records", saved)
    return saved


async def collect_spore(db: AsyncSession) -> int:
    """Fetch spore capture data and store new records."""
    time_range = _build_time_range(hours_back=settings.SPORE_LOOKBACK_HOURS)
    try:
        data = await platform_get(
            "/http/monitor/getBugWarmByCode",
            params={"code": settings.SPORE_CODE, "collectionTime": time_range},
        )
    except Exception as exc:
        logger.error("collect_spore error: %s", exc)
        db.add(CollectLog(task_name="spore", status="error", message=str(exc)))
        await db.commit()
        return 0

    records_data = _extract_records(data)
    parsed_items = []
    for item in records_data:
        col_time = _parse_collection_time(item)
        if col_time is not None:
            parsed_items.append((item, col_time))

    existing_times = await _existing_collection_times(
        db, SporeRecord, settings.SPORE_CODE, [col_time for _, col_time in parsed_items]
    )

    saved = 0
    for item, col_time in parsed_items:
        if col_time in existing_times:
            continue
        try:
            spore_data = _parse_species(item.get("style") or item.get("sporeList") or [])
            total = sum(spore_data.values()) or int(
                item.get("totalCount") or item.get("total") or item.get("value") or 0
            )

            db.add(
                SporeRecord(
                    device_code=settings.SPORE_CODE,
                    collection_time=col_time,
                    total_count=total,
                    spore_data=spore_data,
                    image_url=_extract_image_url(item),
                    raw_data=item,
                )
            )
            saved += 1
        except Exception as exc:
            logger.warning("Failed to parse spore record: %s | data=%s", exc, item)

    db.add(CollectLog(task_name="spore", status="success", records_count=saved))
    await db.commit()
    logger.info("collect_spore: saved %s records", saved)
    return saved
