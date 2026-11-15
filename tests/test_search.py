"""
tests/test_search.py
Integration tests for the FastAPI search endpoints.
Uses httpx.AsyncClient to test against the app directly (no running server needed).
"""
import io
import pytest
from httpx import AsyncClient, ASGITransport
from PIL import Image

from backend.main import app


def _make_test_image_bytes() -> bytes:
    img = Image.new("RGB", (100, 100), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_text_search_empty_query_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/search/text", data={"query": "   "})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_text_search_too_long_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/search/text", data={"query": "x" * 201})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_image_search_wrong_type_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/search/image",
            files={"file": ("test.gif", b"GIF89a...", "image/gif")},
        )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_text_search_uses_mocked_service(monkeypatch):
    from unittest.mock import AsyncMock
    service = AsyncMock(return_value={'query_type': 'text', 'results': [], 'total': 0})
    monkeypatch.setattr('backend.routers.search.search_by_text', service)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post('/search/text', data={'query': ' blue dress ', 'category': 'Dresses'})
    assert response.status_code == 200
    assert response.json() == {'query_type': 'text', 'results': [], 'total': 0}
    service.assert_awaited_once_with('blue dress', {'category': 'Dresses'})
