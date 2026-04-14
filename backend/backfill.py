import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from collectors.insect import collect_insect, collect_spore
from collectors.sensor import collect_weather, collect_soil
from config import settings
from database import Base, engine, init_db

logging.basicConfig(level=logging.INFO)

async def backfill():
    await init_db()
    
    # Patch the _build_time_range in collectors to use 7 days
    import collectors.insect
    import collectors.sensor
    from datetime import datetime, timedelta

    def wide_range(hours_back=None):
        target_hours = 168
        end = datetime.now()
        start = end - timedelta(hours=target_hours)
        fmt = "%Y-%m-%d %H:%M:%S"
        return f"{start.strftime(fmt)},{end.strftime(fmt)}"

    collectors.insect._build_time_range = wide_range
    collectors.sensor._build_time_range = wide_range

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        print("Starting backfill collection (7 days)...")
        await collect_insect(db)
        await collect_spore(db)
        await collect_weather(db)
        await collect_soil(db)
        print("Backfill complete.")

if __name__ == "__main__":
    asyncio.run(backfill())
