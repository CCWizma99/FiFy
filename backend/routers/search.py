"""
backend/routers/search.py
POST /search/image  — image upload → CLIP embed → Qdrant → results
POST /search/text   — text query  → CLIP embed → Qdrant → results
"""
from fastapi import APIRouter, UploadFile, File, Form

from backend.models.search import SearchResponse
from backend.services.search_service import search_by_image, search_by_text
from backend.utils.validators import validate_image, validate_text_query

router = APIRouter()


@router.post("/image", response_model=SearchResponse)
async def image_search(
    file: UploadFile = File(...),
    category: str | None = Form(None),
    gender: str | None = Form(None),
    min_price: float | None = Form(None),
    max_price: float | None = Form(None),
):
    """
    Accept a fashion image upload and return visually similar products.
    Optional filters: category, gender, price range.
    """
    image_bytes = await validate_image(file)
    filters = {k: v for k, v in {
        "category": category,
        "gender": gender,
        "min_price": min_price,
        "max_price": max_price,
    }.items() if v is not None}
    return await search_by_image(image_bytes, filters)


@router.post("/text", response_model=SearchResponse)
async def text_search(
    query: str = Form(...),
    category: str | None = Form(None),
    gender: str | None = Form(None),
    min_price: float | None = Form(None),
    max_price: float | None = Form(None),
):
    """
    Accept a text description and return semantically matched products.
    """
    clean_query = validate_text_query(query)
    filters = {k: v for k, v in {
        "category": category,
        "gender": gender,
        "min_price": min_price,
        "max_price": max_price,
    }.items() if v is not None}
    return await search_by_text(clean_query, filters)
