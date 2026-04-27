"""Seed the SQLite database with 30 days of realistic insect/spore mock data.

Run from the backend directory:
    uv run python scripts/seed_data.py

Inserts data into:
  - insect_records    (twice a day, at 06:00 and 20:00)
  - spore_records     (once a day, at 08:00)
"""

from __future__ import annotations

import asyncio
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Make sure we can import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine, Base
from models import InsectRecord, SporeRecord
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DAYS = 30
INSECT_CODE = "202603172301"
SPORE_CODE = "202603172302"

INSECT_SPECIES = [
    "\u751c\u83dc\u767d\u5e26\u91ce\u87ba",  # 甜菜白带野螟
    "\u5927\u87ba",                            # 大螟
    "\u659c\u7eb9\u591c\u86fe",               # 斜纹夜蛾
    "\u5c0f\u83dc\u86fe",                      # 小菜蛾
    "\u7a3b\u7eb5\u5377\u53f6\u87ba",         # 稻纵卷叶螟
    "\u4e8c\u5316\u87ba",                      # 二化螟
    "\u68c9\u94c3\u866b",                      # 棉铃虫
]
SPORE_TYPES = [
    "\u7a3b\u761f\u75c5\u83cc\u5b62\u5b50",   # 稻瘟病菌孢子
    "\u767d\u7c89\u75c5\u83cc\u5b62\u5b50",   # 白粉病菌孢子
    "\u7070\u9709\u75c5\u83cc\u5b62\u5b50",   # 灰霉病菌孢子
    "\u9508\u75c5\u83cc\u5b62\u5b50",          # 锈病菌孢子
]
def _smooth_noise(base: float, amp: float, seed: float) -> float:
    """Return base + amplitude * sin-based smooth noise."""
    return base + amp * math.sin(seed) + random.uniform(-amp * 0.3, amp * 0.3)


async def seed(session: AsyncSession) -> None:
    # Clear existing seed data to avoid duplicates
    for tbl in ("insect_records", "spore_records"):
        await session.execute(text(f"DELETE FROM {tbl}"))
    await session.commit()
    print("Cleared existing records.")

    now = datetime.now().replace(second=0, microsecond=0)
    start = now - timedelta(days=DAYS - 1)
    start = start.replace(hour=0, minute=0)

    insect_rows: list[InsectRecord] = []
    spore_rows: list[SporeRecord] = []

    for day_i in range(DAYS):
        day_base = start + timedelta(days=day_i)
        day_seed = day_i * 1.3  # for smooth inter-day variation

        # ── Insects: 06:00 and 20:00 ────────────────────────────────────────
        for hour in (6, 20):
            t = day_base.replace(hour=hour)
            peak_factor = 1 + 0.5 * math.sin(math.pi * day_i / DAYS)
            total = max(0, int(_smooth_noise(80 * peak_factor, 30, day_seed + hour)))
            weights = [random.uniform(0.5, 1.5) for _ in INSECT_SPECIES]
            w_sum = sum(weights)
            species_data: dict[str, int] = {}
            remaining = total
            for idx, sp in enumerate(INSECT_SPECIES[:-1]):
                cnt = int(total * weights[idx] / w_sum)
                species_data[sp] = cnt
                remaining -= cnt
            species_data[INSECT_SPECIES[-1]] = max(0, remaining)

            insect_rows.append(InsectRecord(
                device_code=INSECT_CODE,
                collection_time=t,
                total_count=total,
                species_data=species_data,
                image_url=None,
                raw_data={},
            ))

        # ── Spores: 08:00 ──────────────────────────────────────────────────
        t = day_base.replace(hour=8)
        has_spores = random.random() < 0.65
        if has_spores:
            total_spore = max(5, int(_smooth_noise(45, 25, day_seed * 1.7)))
            weights = [random.uniform(0.3, 1.0) for _ in SPORE_TYPES]
            w_sum = sum(weights)
            spore_data: dict[str, int] = {}
            remaining = total_spore
            for idx, sp in enumerate(SPORE_TYPES[:-1]):
                cnt = int(total_spore * weights[idx] / w_sum)
                spore_data[sp] = cnt
                remaining -= cnt
            spore_data[SPORE_TYPES[-1]] = max(0, remaining)
        else:
            total_spore = 0
            spore_data = {}

        spore_rows.append(SporeRecord(
            device_code=SPORE_CODE,
            collection_time=t,
            total_count=total_spore,
            spore_data=spore_data,
            image_url=None,
            raw_data={},
        ))

    print(f"Inserting {len(insect_rows)} insect records...")
    session.add_all(insect_rows)
    print(f"Inserting {len(spore_rows)} spore records...")
    session.add_all(spore_rows)
    await session.commit()
    print("Done! Seed data inserted successfully.")


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
