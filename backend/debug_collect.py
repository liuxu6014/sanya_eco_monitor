import asyncio
import os
import httpx
import logging
from datetime import datetime, timedelta
from config import settings
from collectors.base import platform_get

logging.basicConfig(level=logging.INFO)

def _build_time_range(hours_back: int = 168) -> str:
    end = datetime.now()
    start = end - timedelta(hours=hours_back)
    fmt = "%Y-%m-%d %H:%M:%S"
    return f"{start.strftime(fmt)},{end.strftime(fmt)}"

async def debug_fetch():
    time_range = _build_time_range()
    print(f"Checking for device: {settings.INSECT_CODE} with range: {time_range}")
    try:
        data = await platform_get(
            "/http/monitor/getBugWarmByCode",
            params={"code": settings.INSECT_CODE, "collectionTime": time_range},
        )
        print("--- Insect Raw Data ---")
        print(data)
        items = data.get("data") or []
        if not isinstance(items, list): items = [items]
        print(f"Found {len(items)} insect items")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Insect fetch failed: {e}")

    try:
        data = await platform_get(
            "/http/monitor/getBugWarmByCode",
            params={"code": settings.SPORE_CODE, "collectionTime": time_range},
        )
        print("\n--- Spore Raw Data ---")
        print(data)
        items = data.get("data") or []
        if not isinstance(items, list): items = [items]
        print(f"Found {len(items)} spore items")
    except Exception as e:
        print(f"Spore fetch failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_fetch())
