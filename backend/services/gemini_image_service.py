"""Gemini AI image generation service.

Uses the Gemini REST API (httpx, no SDK) to generate illustrative images
for agricultural monitoring reports:

  • 封面配图  — aerial/landscape scene of the monitoring area
  • 虫种图鉴  — one reference illustration per top insect species
  • 病害图示  — fungal/spore disease risk illustration (when spore count > 0)

All images are returned as base64-encoded PNG/JPEG strings ready for
embedding in <img src="data:image/...;base64,..."> tags.

The Gemini image-generation REST endpoint (v1beta):
  POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
  Headers: x-goog-api-key: {api_key}
  Body:
    {
      "contents": [{"parts": [{"text": "..."}]}],
      "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
    }
  Response:
    candidates[0].content.parts[n].inlineData.data  -> base64 image bytes
    candidates[0].content.parts[n].inlineData.mimeType -> "image/png" etc.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

_GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/{model}:generateContent"
)

# ---------------------------------------------------------------------------
# Randomized prompt builders — each call returns a varied prompt
# ---------------------------------------------------------------------------

def _cover_prompt() -> str:
    time = random.choice(["golden-hour sunrise", "soft morning mist", "blue-hour dusk", "midday tropical sun", "overcast diffused light"])
    scene = random.choice([
        "lush green paddy fields and rubber tree plantations",
        "betel nut palm groves and loquat orchards with irrigation channels",
        "mixed tropical agroforestry with terraced fields",
        "rubber tree rows stretching to the horizon with distant mountains",
        "panoramic view of agricultural monitoring stations amid green cropland",
    ])
    style = random.choice(["drone aerial view", "high-altitude aerial photograph", "satellite-style aerial shot"])
    return (
        f"Professional {style} of tropical agricultural fields in Tianya District, Sanya, "
        f"Hainan Province, China. Show {scene} under clear subtropical sky. "
        f"Photorealistic, high resolution, wide landscape orientation, {time}, no text, no watermark."
    )


def _disease_prompt() -> str:
    crop = random.choice(["rice plants", "rubber tree leaves", "betel nut palm fronds", "loquat orchard foliage"])
    atmosphere = random.choice(["dawn mist", "humid tropical air", "early morning fog", "post-rain moisture"])
    view = random.choice([
        "Show magnified fungal spores floating in the air",
        "Show microscopic view of fungal hyphae spreading on leaf surface",
        "Show spore clouds drifting across",
        "Show airborne fungal particles dispersing over",
    ])
    return (
        f"Scientific illustration of fungal spore dispersal in Hainan Province. "
        f"{view} {crop}, with {atmosphere} in the background. "
        f"Photorealistic, dramatic lighting, no text, wide format."
    )


def _weather_prompt() -> str:
    time = random.choice(["sunrise", "midday", "stormy afternoon", "clear evening", "overcast morning"])
    detail = random.choice([
        "anemometer spinning in wind",
        "rain gauge collecting droplets",
        "temperature and humidity sensor array",
        "solar radiation sensor glinting in light",
        "full automatic weather station array",
    ])
    return (
        f"Photorealistic weather observation scene in tropical Sanya, Hainan at {time}. "
        f"Show {detail} standing in a lush green agricultural field with dramatic sky. "
        f"Wide angle, high detail, no text, no watermark."
    )


def _rainfall_prompt() -> str:
    intensity = random.choice(["gentle drizzle", "steady tropical rain", "heavy downpour", "light shower after storm"])
    scene = random.choice([
        "rain gauge in a green paddy field",
        "water droplets on broad tropical leaves",
        "flooded field furrows reflecting grey sky",
        "rain falling on rubber tree canopy",
    ])
    return (
        f"Photorealistic scene of {intensity} in tropical Sanya agricultural area. "
        f"Show {scene}. Moody natural lighting, water reflections, no text, no watermark."
    )


def _soil_prompt() -> str:
    style = random.choice([
        "scientific cross-section diagram with clean labels",
        "photorealistic soil core sample",
        "artistic cutaway illustration",
        "3D rendered soil profile visualization",
    ])
    detail = random.choice([
        "blue moisture gradient bands at 10cm, 20cm, 40cm depth",
        "root networks visible threading through each layer",
        "color gradient from dark topsoil to lighter subsoil",
        "moisture sensors embedded at three depths with readings",
    ])
    return (
        f"{style} of tropical agricultural soil layers in Hainan. "
        f"Show {detail}. Rich red-brown tropical soil, wide format, no text, no watermark."
    )


def _runoff_prompt() -> str:
    forest = random.choice(["rubber tree plantation", "loquat orchard", "betel nut grove", "secondary tropical forest", "mixed agroforestry"])
    time = random.choice(["after heavy rain", "in morning mist", "during dry season low flow", "at peak rainy season"])
    return (
        f"Photorealistic scene of forest runoff monitoring {time} in {forest}, Tianya District Hainan. "
        f"Show a natural stream with automated flow monitoring sensors on the bank. "
        f"Lush tropical vegetation, natural lighting, no text, no watermark, wide format."
    )


def _pollution_prompt() -> str:
    view = random.choice(["aerial drone view", "ground-level wide shot", "elevated perspective"])
    feature = random.choice([
        "retention pond and vegetated buffer strips",
        "water quality sensor buoy in irrigation canal",
        "constructed wetland filtering agricultural runoff",
        "monitoring station beside paddy field drainage ditch",
    ])
    return (
        f"{view} of agricultural non-point source pollution monitoring in Hainan. "
        f"Show {feature} amid lush green tropical farmland. "
        f"Photorealistic, clear water, no text, no watermark."
    )


def _forest_ecology_prompt() -> str:
    time = random.choice(["misty morning", "golden afternoon", "after tropical rain", "dawn with low clouds"])
    focus = random.choice([
        "rubber trees (Hevea brasiliensis) with tapping cuts on bark",
        "betel nut palms (Areca catechu) with fruit clusters",
        "loquat orchard rows with fruit-laden branches",
        "mixed canopy of rubber, betel nut and loquat trees",
        "forest floor biodiversity with ferns and understory plants",
    ])
    return (
        f"Photorealistic {time} landscape of {focus} in Tianya District, Sanya. "
        f"Lush green subtropical atmosphere, rich ecological detail, wide panoramic format, "
        f"no text, no watermark."
    )


def _smart_devices_prompt() -> str:
    time = random.choice(["sunrise", "blue hour", "midday", "dusk"])
    focus = random.choice([
        "insect light trap glowing at night with moths circling",
        "weather station and soil sensors array in green field",
        "spore capture device with collection funnel in morning light",
        "IoT monitoring pole with multiple sensors and solar panel",
        "field camera monitoring seedling growth stage",
    ])
    return (
        f"Photorealistic {time} scene of smart agriculture IoT monitoring in tropical Hainan. "
        f"Show {focus}. High-tech meets nature aesthetic, dramatic lighting, "
        f"no text, no watermark, wide format."
    )


def _pest_prompt(species_name: str) -> str:
    background = random.choice([
        "on a green rice leaf in natural field lighting",
        "resting on a rice stem with blurred paddy field background",
        "on a tropical plant leaf with natural bokeh background",
        "on bark with natural outdoor lighting",
        "among rice plant stems in a real paddy field",
    ])
    lighting = random.choice([
        "natural daylight, sharp focus",
        "soft outdoor diffused light, macro detail",
        "morning natural light, high sharpness",
        "field conditions, realistic colors",
    ])
    return (
        f"Ultra-realistic close-up wildlife photograph of the insect '{species_name}' "
        f"(a real agricultural pest found in Hainan, China), {background}. "
        f"{lighting}. Real insect, photographic realism, NOT illustration, NOT cartoon, "
        f"NOT drawing. Camera photo quality, no text, no watermark, 16:9 landscape format."
    )


# ---------------------------------------------------------------------------
# Core REST call
# ---------------------------------------------------------------------------

async def _call_image_gen(prompt: str, client: httpx.AsyncClient) -> str | None:
    """Call native Gemini image-generation API endpoint and return base64-encoded image string, or None."""
    if not settings.IMAGE_GEN_API_KEY:
        return None

    # Construct URL: https://yinli.one/v1beta/models/{model}:generateContent
    base_url = settings.IMAGE_GEN_BASE_URL.rstrip('/')
    url = f"{base_url}/v1beta/models/{settings.IMAGE_GEN_MODEL}:generateContent"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
            "imageConfig": {"aspectRatio": "16:9"},
        },
    }
    
    try:
        resp = await client.post(
            url,
            headers={"x-goog-api-key": settings.IMAGE_GEN_API_KEY},
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        for part in parts:
            inline = part.get("inlineData")
            if inline:
                mime = inline.get("mimeType", "image/png")
                b64 = inline.get("data", "")
                return f"data:{mime};base64,{b64}"
    except httpx.HTTPStatusError as e:
        logger.error("Image gen API HTTP error: %s %s", e.response.status_code, e.response.text[:200])
    except Exception as e:
        logger.error("Image gen API error: %s", e)
    return None


# ---------------------------------------------------------------------------
# Per-image generators
# ---------------------------------------------------------------------------

async def _cover_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_cover_prompt(), client)

async def _disease_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_disease_prompt(), client)

async def _weather_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_weather_prompt(), client)

async def _rainfall_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_rainfall_prompt(), client)

async def _soil_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_soil_prompt(), client)

async def _runoff_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_runoff_prompt(), client)

async def _pollution_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_pollution_prompt(), client)

async def _forest_ecology_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_forest_ecology_prompt(), client)

async def _smart_devices_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_smart_devices_prompt(), client)

async def _pest_image(species_name: str, client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_pest_prompt(species_name), client)

# kept for backward compatibility
async def _spore_disease_image(client: httpx.AsyncClient) -> str | None:
    return await _disease_image(client)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_report_images(summary: dict[str, Any]) -> dict[str, Any]:
    """Generate all AI images for the report concurrently.

    Returns a dict:
      {
        "cover":           str | None,
        "weather":         str | None,
        "rainfall":        str | None,
        "soil":            str | None,
        "runoff":          str | None,
        "disease":         str | None,
        "pollution":       str | None,
        "forest_ecology":  str | None,
        "smart_devices":   str | None,
        "pests":           {"虫种名": str | None, ...},  # top 3 species
      }
    """
    if not settings.IMAGE_GEN_API_KEY:
        logger.info("IMAGE_GEN_API_KEY not configured — skipping AI image generation")
        return {
            "cover": None, "weather": None, "rainfall": None, "soil": None,
            "runoff": None, "disease": None, "pollution": None,
            "forest_ecology": None, "smart_devices": None, "pests": {},
        }

    top_species = (summary.get("insect") or {}).get("top_species") or []
    top3 = [item[0] for item in top_species[:3] if item]
    has_spores = (summary.get("spore") or {}).get("total_count", 0) > 0
    has_weather = (summary.get("weather") or {}).get("records_count", 0) > 0

    async with httpx.AsyncClient() as client:
        tasks: dict[str, asyncio.Task[str | None]] = {
            "cover": asyncio.create_task(_cover_image(client)),
            "smart_devices": asyncio.create_task(_smart_devices_image(client)),
            "forest_ecology": asyncio.create_task(_forest_ecology_image(client)),
        }
        if has_weather:
            tasks["weather"] = asyncio.create_task(_weather_image(client))
        if has_spores:
            tasks["disease"] = asyncio.create_task(_disease_image(client))

        pest_tasks = [
            (name, asyncio.create_task(_pest_image(name, client)))
            for name in top3
        ]

        results: dict[str, Any] = {
            "cover": None,
            "weather": None,
            "rainfall": None,
            "soil": None,
            "runoff": None,
            "disease": None,
            "pollution": None,
            "forest_ecology": None,
            "smart_devices": None,
            "pests": {},
        }
        for key, task in tasks.items():
            results[key] = await task
        for name, task in pest_tasks:
            results["pests"][name] = await task

    logger.info(
        "Image generation complete: %d images generated",
        sum(1 for k, v in results.items() if k != "pests" and v)
        + sum(1 for v in results["pests"].values() if v),
    )
    return results
