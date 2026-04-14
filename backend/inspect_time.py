import asyncio
import httpx
import json
from config import settings
from collectors.base import get_token

async def inspect_time():
    token = await get_token()
    headers = {"Authorization": token}
    target_time = "2026-04-04 02:41:00,2026-04-04 02:41:59"
    
    for code in [settings.WEATHER_CODE, settings.SOIL_CODE]:
        print(f"\n--- Code: {code} at {target_time} ---")
        resp = await httpx.AsyncClient(verify=False).get(
            f"{settings.SENSOR_BASE_URL}/http/monitor/getSensorByCode",
            params={"code": code, "collectionTime": target_time},
            headers=headers
        )
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(inspect_time())
