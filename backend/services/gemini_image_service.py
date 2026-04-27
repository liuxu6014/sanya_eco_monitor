"""Gemini AI image generation service.

Uses the Gemini REST API (httpx, no SDK) to generate illustrative images
for agricultural monitoring reports:

  • 封面配图  — aerial/landscape scene of the monitoring area
  • 虫种图鉴  — one reference illustration per top insect species
  • 病害图示  — fungal/spore disease risk illustration (when spore count > 0)

All images are returned as base64-encoded PNG/JPEG strings ready for
embedding in <img src="data:image/...;base64,..."> tags.
"""

from __future__ import annotations

import asyncio
import logging
import random
import base64
import io
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


def _empty_image_bundle() -> dict[str, Any]:
    return {
        "cover": None,
        "disease": None,
        "forest_ecology": None,
        "smart_devices": None,
        "pests": {},
    }

# ---------------------------------------------------------------------------
# Randomized prompt builders — each call returns a varied prompt
# ---------------------------------------------------------------------------

def _cover_prompt() -> str:
    time = random.choice(["golden-hour sunrise", "soft morning mist", "blue-hour dusk", "midday tropical sun", "overcast diffused light"])
    scene = random.choice([
        "lush green rubber forest and terraced farmland",
        "rubber tree plantations with secondary forest growth",
        "panoramic view of Sanya rubber forests under near-naturalization",
        "agricultural monitoring stations amid rubber trees and loquat orchards",
        "lush tropical agroforestry with complex tree layers",
    ])
    style = random.choice(["drone aerial view", "high-altitude aerial photograph", "satellite-style aerial shot"])
    return (
        f"Professional {style} of tropical rubber forest in Tianya District, Sanya, "
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


def _forest_ecology_prompt() -> str:
    time = random.choice(["misty morning", "golden afternoon", "after tropical rain", "dawn with low clouds"])
    focus = random.choice([
        "rubber trees (Hevea brasiliensis) with tapping cuts on bark",
        "complex forest floor biodiversity with ferns and understory plants",
        "mixed canopy of rubber, betel nut and loquat trees",
        "near-naturalized forest structure with multiple vegetation layers",
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
        "runoff sensors and rain gauges in a natural rubber forest",
        "spore capture device with collection funnel in morning light",
        "IoT monitoring pole with solar panel amid tropical trees",
    ])
    return (
        f"Photorealistic {time} scene of smart forest IoT monitoring in tropical Hainan. "
        f"Show {focus}. High-tech meets nature aesthetic, dramatic lighting, "
        f"no text, no watermark, wide format."
    )


def _pest_prompt(species_name: str) -> str:
    background = random.choice([
        "on a green leaf in natural field lighting",
        "resting on bark with blurred forest background",
        "on a tropical plant leaf with natural bokeh background",
        "among forest floor plants in a real rubber grove",
    ])
    lighting = random.choice([
        "natural daylight, sharp focus",
        "soft outdoor diffused light, macro detail",
        "field conditions, realistic colors",
    ])
    return (
        f"Ultra-realistic close-up wildlife photograph of the insect '{species_name}' "
        f"(a real agricultural/forest pest found in Hainan, China), {background}. "
        f"{lighting}. Real insect, photographic realism, no text, no watermark, 16:9 landscape format."
    )


# ---------------------------------------------------------------------------
# Core REST call
# ---------------------------------------------------------------------------


def _is_gemini_model(model: str) -> bool:
    return model.lower().startswith("gemini")


def _is_openai_compatible_base(base_url: str) -> bool:
    return "/v1" in base_url and "googleapis.com" not in base_url


def _candidate_gemini_urls(base_url: str, model: str) -> list[str]:
    root = base_url.rstrip("/")
    candidates: list[str] = []

    if root.endswith("/v1"):
        base_root = root[:-3]
        candidates.extend(
            [
                f"{base_root}/v1beta/models/{model}:generateContent",
                f"{base_root}/v1/models/{model}:generateContent",
                f"{root}/models/{model}:generateContent",
            ]
        )
    elif root.endswith("/v1beta"):
        base_root = root[:-7]
        candidates.extend(
            [
                f"{root}/models/{model}:generateContent",
                f"{base_root}/v1/models/{model}:generateContent",
            ]
        )
    else:
        candidates.extend(
            [
                f"{root}/v1beta/models/{model}:generateContent",
                f"{root}/v1/models/{model}:generateContent",
                f"{root}/models/{model}:generateContent",
            ]
        )

    # Deduplicate while preserving order.
    return list(dict.fromkeys(candidates))


def _extract_openai_image(data: dict[str, Any]) -> str | None:
    items = data.get("data")
    if not items:
        return None
    first = items[0]
    b64 = first.get("b64_json")
    if b64:
        return f"data:image/png;base64,{b64}"
    img_url = first.get("url")
    if img_url:
        return img_url
    return None


def _extract_gemini_image(data: dict[str, Any]) -> str | None:
    for candidate in data.get("candidates", []):
        parts = candidate.get("content", {}).get("parts", [])
        for part in parts:
            inline = part.get("inlineData") or {}
            b64 = inline.get("data")
            if b64:
                mime = inline.get("mimeType", "image/png")
                return f"data:{mime};base64,{b64}"
    return None


def _build_gemini_payload(prompt: str, model: str) -> dict[str, Any]:
    image_config: dict[str, Any] = {"aspectRatio": "16:9"}
    if "3-pro-image-preview" in model or "3.1-flash-image-preview" in model:
        image_config["imageSize"] = "2K"
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "imageConfig": image_config,
        },
    }

async def _call_image_gen(prompt: str, client: httpx.AsyncClient) -> str | None:
    """Call image-generation API. Supports both Gemini-native and OpenAI-compliant endpoints."""
    if not settings.IMAGE_GEN_API_KEY:
        return None

    base_url = settings.IMAGE_GEN_BASE_URL.rstrip('/')
    model = settings.IMAGE_GEN_MODEL

    payload = _build_gemini_payload(prompt, model)

    prefer_gemini = _is_gemini_model(model)

    try:
        if prefer_gemini:
            for url in _candidate_gemini_urls(base_url, model):
                for request_kwargs in (
                    {"params": {"key": settings.IMAGE_GEN_API_KEY}},
                    {"headers": {"x-goog-api-key": settings.IMAGE_GEN_API_KEY}},
                    {"headers": {"Authorization": f"Bearer {settings.IMAGE_GEN_API_KEY}"}},
                ):
                    try:
                        resp = await client.post(
                            url,
                            json=payload,
                            timeout=60,
                            **request_kwargs,
                        )
                        resp.raise_for_status()
                        image = _extract_gemini_image(resp.json())
                        if image:
                            return image
                    except httpx.HTTPStatusError as exc:
                        logger.warning(
                            "Gemini image endpoint failed: %s %s %s",
                            exc.response.status_code,
                            url,
                            exc.response.text[:200],
                        )
                    except Exception as exc:
                        logger.warning("Gemini image endpoint error on %s: %s", url, exc)
            return None

        if _is_openai_compatible_base(base_url):
            url = f"{base_url}/images/generations"
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.IMAGE_GEN_API_KEY}"},
                json={
                    "model": model,
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "response_format": "b64_json"
                },
                timeout=60,
            )
            resp.raise_for_status()
            image = _extract_openai_image(resp.json())
            if image:
                return image

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

async def _forest_ecology_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_forest_ecology_prompt(), client)

async def _smart_devices_image(client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_smart_devices_prompt(), client)

async def _pest_image(species_name: str, client: httpx.AsyncClient) -> str | None:
    return await _call_image_gen(_pest_prompt(species_name), client)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_report_images(summary: dict[str, Any]) -> dict[str, Any]:
    """Generate all AI images for the report concurrently."""
    if not settings.ENABLE_AI_IMAGE_GEN:
        logger.info("AI image generation disabled by config, skipping AI image generation")
        return _empty_image_bundle()
    if not settings.IMAGE_GEN_API_KEY:
        logger.info("IMAGE_GEN_API_KEY not configured — skipping AI image generation")
        return _empty_image_bundle()

    top_species = (summary.get("insect") or {}).get("top_species") or []
    top3 = [item[0] for item in top_species[:3] if item]
    has_spores = (summary.get("spore") or {}).get("total_count", 0) > 0

    async with httpx.AsyncClient() as client:
        tasks = {
            "cover": asyncio.create_task(_cover_image(client)),
            "smart_devices": asyncio.create_task(_smart_devices_image(client)),
            "forest_ecology": asyncio.create_task(_forest_ecology_image(client)),
        }
        if has_spores:
            tasks["disease"] = asyncio.create_task(_disease_image(client))

        pest_tasks = [
            (name, asyncio.create_task(_pest_image(name, client)))
            for name in top3
        ]

        results: dict[str, Any] = _empty_image_bundle()
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
