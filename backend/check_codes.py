import asyncio
import httpx
from config import settings
from collectors.base import get_token

async def check_codes():
    token = await get_token()
    headers = {"Authorization": token}
    codes = [settings.WEATHER_CODE, settings.SOIL_CODE]
    
    for code in codes:
        print(f"\n--- Checking Code: {code} ---")
        try:
            resp = await httpx.AsyncClient(verify=False).get(
                f"{settings.SENSOR_BASE_URL}/http/monitor/getSensorByCode",
                params={"code": code, "collectionTime": "2026-04-04 00:00:00,2026-04-04 23:59:59"},
                headers=headers
            )
            data = resp.json()
            items = data.get("data", {}).get("list", [])
            print(f"Found {len(items)} records.")
            if items:
                print("First record keys:", list(items[0].keys()))
                # Check for specific keys
                soil_keys = [k for k in items[0].keys() if "土壤" in k]
                weather_keys = [k for k in items[0].keys() if "气" in k or "风" in k]
                print(f"Soil-related keys: {soil_keys}")
                print(f"Weather-related keys: {weather_keys}")
        except Exception as e:
            print(f"Error checking code {code}: {e}")

if __name__ == "__main__":
    asyncio.run(check_codes())
