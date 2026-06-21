import asyncio
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import image_quality  # noqa: E402


class _FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


class _FakeClient:
    def __init__(self, content: bytes):
        self._content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, _url):
        return _FakeResponse(self._content)


def _make_grayscale_jpeg(value: int) -> bytes:
    image = Image.new("L", (64, 64), color=value)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _make_structured_placeholder_jpeg() -> bytes:
    image = Image.new("L", (64, 64), color=128)
    for y in range(8):
        for x in range(64):
            image.putpixel((x, y), 0 if x < 16 else 96)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


class ImageQualityTests(unittest.TestCase):
    def setUp(self):
        image_quality._RESULT_CACHE.clear()

    def test_near_black_image_is_filtered(self):
        content = _make_grayscale_jpeg(18)

        async def run():
            with patch("services.image_quality.httpx.AsyncClient", return_value=_FakeClient(content)):
                return await image_quality.is_probably_black_image("https://example.com/dark.jpg")

        result = asyncio.run(run())
        self.assertTrue(result)

    def test_low_variance_placeholder_image_is_filtered(self):
        content = _make_grayscale_jpeg(127)

        async def run():
            with patch("services.image_quality.httpx.AsyncClient", return_value=_FakeClient(content)):
                return await image_quality.is_probably_black_image("https://example.com/placeholder.jpg")

        result = asyncio.run(run())
        self.assertTrue(result)

    def test_structured_placeholder_image_is_filtered(self):
        content = _make_structured_placeholder_jpeg()

        async def run():
            with patch("services.image_quality.httpx.AsyncClient", return_value=_FakeClient(content)):
                return await image_quality.is_probably_black_image("https://example.com/segmented-placeholder.jpg")

        result = asyncio.run(run())
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
