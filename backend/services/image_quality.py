from __future__ import annotations

import io

import httpx
from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError


_REQUEST_TIMEOUT = 8.0
_THUMBNAIL_SIZE = (64, 64)
_BLACK_PIXEL_THRESHOLD = 12
_NEAR_BLACK_RATIO_THRESHOLD = 0.98
_AVERAGE_BRIGHTNESS_THRESHOLD = 8
_DARK_PIXEL_THRESHOLD = 28
_DARK_RATIO_THRESHOLD = 0.68
_DARK_AVERAGE_BRIGHTNESS_THRESHOLD = 42
_LOW_VARIANCE_STD_THRESHOLD = 6
_LOW_VARIANCE_UNIQUE_THRESHOLD = 16
_STRUCTURED_PLACEHOLDER_TOP_ROWS = 8
_STRUCTURED_PLACEHOLDER_TOP_DARK_RATIO_THRESHOLD = 0.12
_STRUCTURED_PLACEHOLDER_BODY_STD_THRESHOLD = 2
_STRUCTURED_PLACEHOLDER_BODY_UNIQUE_THRESHOLD = 8
_RESULT_CACHE: dict[str, bool] = {}

ImageFile.LOAD_TRUNCATED_IMAGES = True



async def is_probably_black_image(url: str | None) -> bool:
    if not url:
        return False

    if url in _RESULT_CACHE:
        return _RESULT_CACHE[url]

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        image.load()
        image = ImageOps.exif_transpose(image).convert("L")
        image.thumbnail(_THUMBNAIL_SIZE)
        pixels = list(image.tobytes())
        if not pixels:
            return False

        near_black_ratio = sum(1 for value in pixels if value <= _BLACK_PIXEL_THRESHOLD) / len(pixels)
        dark_ratio = sum(1 for value in pixels if value <= _DARK_PIXEL_THRESHOLD) / len(pixels)
        average_brightness = sum(pixels) / len(pixels)
        unique_values = len(set(pixels))
        variance = sum((value - average_brightness) ** 2 for value in pixels) / len(pixels)
        std_dev = variance ** 0.5
        is_pure_black = (
            near_black_ratio >= _NEAR_BLACK_RATIO_THRESHOLD
            and average_brightness <= _AVERAGE_BRIGHTNESS_THRESHOLD
        )
        is_dark_black = (
            dark_ratio >= _DARK_RATIO_THRESHOLD
            and average_brightness <= _DARK_AVERAGE_BRIGHTNESS_THRESHOLD
        )
        is_flat_placeholder = (
            std_dev <= _LOW_VARIANCE_STD_THRESHOLD
            and unique_values <= _LOW_VARIANCE_UNIQUE_THRESHOLD
        )
        is_structured_placeholder = _is_structured_placeholder(image)
        is_black = is_pure_black or is_dark_black or is_flat_placeholder or is_structured_placeholder
        _remember_result(url, is_black)
        return is_black
    except (httpx.HTTPError, OSError, UnidentifiedImageError, ValueError):
        _remember_result(url, True)
        return True


def _remember_result(url: str, is_black: bool) -> None:
    if len(_RESULT_CACHE) >= 512:
        _RESULT_CACHE.pop(next(iter(_RESULT_CACHE)))
    _RESULT_CACHE[url] = is_black


def _is_structured_placeholder(image: Image.Image) -> bool:
    width, height = image.size
    if width <= 0 or height <= _STRUCTURED_PLACEHOLDER_TOP_ROWS:
        return False

    top_rows = min(_STRUCTURED_PLACEHOLDER_TOP_ROWS, height - 1)
    top_pixels: list[int] = []
    body_pixels: list[int] = []

    for y in range(height):
        for x in range(width):
            value = image.getpixel((x, y))
            if y < top_rows:
                top_pixels.append(value)
            else:
                body_pixels.append(value)

    if not top_pixels or not body_pixels:
        return False

    top_dark_ratio = sum(1 for value in top_pixels if value <= _DARK_PIXEL_THRESHOLD) / len(top_pixels)
    body_mean = sum(body_pixels) / len(body_pixels)
    body_variance = sum((value - body_mean) ** 2 for value in body_pixels) / len(body_pixels)
    body_std_dev = body_variance ** 0.5
    body_unique_values = len(set(body_pixels))

    return (
        top_dark_ratio >= _STRUCTURED_PLACEHOLDER_TOP_DARK_RATIO_THRESHOLD
        and body_std_dev <= _STRUCTURED_PLACEHOLDER_BODY_STD_THRESHOLD
        and body_unique_values <= _STRUCTURED_PLACEHOLDER_BODY_UNIQUE_THRESHOLD
    )
