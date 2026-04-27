from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import get_db
from models import InsectRecord, SporeRecord

router = APIRouter(prefix="/api/insect", tags=["虫情"])


async def _latest_non_empty_image(db: AsyncSession, model) -> str | None:
    result = await db.execute(
        select(model.image_url)
        .where(model.image_url.is_not(None), model.image_url != "")
        .order_by(desc(model.collection_time))
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/latest")
async def get_latest_insect(db: AsyncSession = Depends(get_db)):
    """最新一条虫情记录"""
    result = await db.execute(
        select(InsectRecord).order_by(desc(InsectRecord.collection_time)).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"data": None}
    image_url = record.image_url or await _latest_non_empty_image(db, InsectRecord)
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "total_count": record.total_count,
            "species_data": record.species_data,
            "image_url": image_url,
        }
    }


@router.get("/trend")
async def get_insect_trend(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """近N天虫情趋势 (每日汇总)"""
    since = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= since)
        .order_by(InsectRecord.collection_time)
    )
    records = result.scalars().all()

    # Group by day
    daily: dict = {}
    for r in records:
        day = r.collection_time.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "total": 0, "species": {}}
        daily[day]["total"] += r.total_count
        for name, cnt in (r.species_data or {}).items():
            daily[day]["species"][name] = daily[day]["species"].get(name, 0) + cnt

    return {"data": list(daily.values())}


@router.get("/species-stats")
async def get_species_stats(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """各虫种统计汇总"""
    since = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(InsectRecord).where(InsectRecord.collection_time >= since)
    )
    records = result.scalars().all()

    totals: dict = {}
    for r in records:
        for name, cnt in (r.species_data or {}).items():
            totals[name] = totals.get(name, 0) + cnt

    sorted_species = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    return {
        "data": [{"name": name, "value": cnt} for name, cnt in sorted_species]
    }


@router.get("/spore/latest")
async def get_latest_spore(db: AsyncSession = Depends(get_db)):
    """最新孢子捕捉数据"""
    result = await db.execute(
        select(SporeRecord).order_by(desc(SporeRecord.collection_time)).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"data": None}
    image_url = record.image_url or await _latest_non_empty_image(db, SporeRecord)
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "total_count": record.total_count,
            "spore_data": record.spore_data,
            "image_url": image_url,
        }
    }


@router.get("/spore/trend")
async def get_spore_trend(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """近N天孢子趋势"""
    since = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(SporeRecord)
        .where(SporeRecord.collection_time >= since)
        .order_by(SporeRecord.collection_time)
    )
    records = result.scalars().all()

    daily: dict = {}
    for r in records:
        day = r.collection_time.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "total": 0}
        daily[day]["total"] += r.total_count

    return {"data": list(daily.values())}


@router.get("/combined-trend")
async def get_combined_trend(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """虫情+孢子 联合趋势（逐日，用于相关性分析图）"""
    since = datetime.now() - timedelta(days=days)

    insect_res = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= since)
        .order_by(InsectRecord.collection_time)
    )
    spore_res = await db.execute(
        select(SporeRecord)
        .where(SporeRecord.collection_time >= since)
        .order_by(SporeRecord.collection_time)
    )
    insects = insect_res.scalars().all()
    spores = spore_res.scalars().all()

    insect_daily: dict = {}
    for r in insects:
        day = r.collection_time.strftime("%Y-%m-%d")
        insect_daily[day] = insect_daily.get(day, 0) + r.total_count

    spore_daily: dict = {}
    for r in spores:
        day = r.collection_time.strftime("%Y-%m-%d")
        spore_daily[day] = spore_daily.get(day, 0) + r.total_count

    all_days = sorted(set(list(insect_daily.keys()) + list(spore_daily.keys())))
    data = [
        {
            "date": d,
            "insect": insect_daily.get(d, 0),
            "spore": spore_daily.get(d, 0),
        }
        for d in all_days
    ]
    return {"data": data}


@router.get("/species-heatmap")
async def get_species_heatmap(
    days: int = Query(14, ge=7, le=30),
    db: AsyncSession = Depends(get_db),
):
    """虫种-日期热力图数据（二维矩阵）"""
    since = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= since)
        .order_by(InsectRecord.collection_time)
    )
    records = result.scalars().all()

    # Collect all dates and species
    from collections import defaultdict
    matrix: dict = defaultdict(lambda: defaultdict(int))
    all_dates: set = set()
    all_species: set = set()
    for r in records:
        day = r.collection_time.strftime("%m-%d")
        all_dates.add(day)
        for sp, cnt in (r.species_data or {}).items():
            matrix[day][sp] += cnt
            all_species.add(sp)

    dates = sorted(all_dates)
    species = sorted(all_species)
    # Build flat list: [date_index, species_index, value]
    flat = []
    for di, date in enumerate(dates):
        for si, sp in enumerate(species):
            flat.append([di, si, matrix[date].get(sp, 0)])

    return {"data": {"dates": dates, "species": species, "values": flat}}
