"""
backend/routers/products.py
GET /products/{id} — fetch single product metadata from Qdrant by ID.
"""
from fastapi import APIRouter, HTTPException, Response
import httpx
from backend.services.qdrant_service import get_product_by_id, list_products

router = APIRouter()


@router.get("")
async def get_all_products(
    limit: int = 20,
    category: str | None = None,
    gender: str | None = None,
    q: str | None = None
):
    """Return a list of available products."""
    from backend.utils.logger import get_logger
    _log = get_logger(__name__)
    _log.info("get_all_products called | q=%s | limit=%s | category=%s | gender=%s", q, limit, category, gender)
    filters = {}
    if category and category.lower() != "all":
        filters["category"] = category
    if gender and gender.lower() != "all":
        filters["gender"] = gender
        
    if q:
        from backend.services.search_service import search_by_text
        # We use semantic search for the admin too, as it's the most powerful search we have.
        search_res = await search_by_text(q, filters)
        return search_res.results

    return await list_products(limit, filters)


@router.get("/proxy-image")
async def proxy_image(url: str):
    """
    Proxy an external image URL to avoid hotlinking and bypass 403s.
    In a production app, we'd cache this to a local CDN/storage.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10.0, follow_redirects=True)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch image")
            
            return Response(content=resp.content, media_type=resp.headers.get("content-type", "image/jpeg"))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image proxy error: {str(e)}")


@router.get("/{product_id}")
async def get_product(product_id: str):
    """Return full metadata for a single product by its Qdrant point ID."""
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found.")
    return product
