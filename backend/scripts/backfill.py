import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from collectors.insect import collect_insect, collect_spore
from database import engine, init_db

async def backfill():
    await init_db()

    # Patch the insect collectors to use a 7-day range.
    import collectors.insect
    from datetime import datetime, timedelta

    def wide_range(hours_back=None):
        target_hours = 168
        end = datetime.now()
        start = end - timedelta(hours=target_hours)
        fmt = "%Y-%m-%d %H:%M:%S"
        return f"{start.strftime(fmt)},{end.strftime(fmt)}"

    collectors.insect._build_time_range = wide_range

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        print("Starting backfill collection (7 days)...")
        await collect_insect(db)
        await collect_spore(db)
        print("Backfill complete.")

if __name__ == "__main__":
    asyncio.run(backfill())
