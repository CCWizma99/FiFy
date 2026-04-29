"""
backend/services/search_service.py
Orchestrates the full search pipeline:
  image bytes / text string → embedding → Qdrant → SearchResponse
"""
from backend.models.search import ProductResult, SearchResponse
from backend.services.embedding_service import get_image_embedding, get_text_embedding
from backend.services.qdrant_service import query_similar_products
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def search_by_image(image_bytes: bytes, filters: dict) -> SearchResponse:
    logger.info("Image search | filters=%s", filters)
    vector = await get_image_embedding(image_bytes)
    raw_results = await query_similar_products(vector, vector_name="image", filters=filters)
    return _build_response("image", raw_results)


async def search_by_text(query: str, filters: dict) -> SearchResponse:
    logger.info("Text search | query='%s' | filters=%s", query, filters)
    vector = await get_text_embedding(query)
    raw_results = await query_similar_products(vector, vector_name="text", filters=filters)
    return _build_response("text", raw_results)


def _build_response(query_type: str, raw_results: list[dict]) -> SearchResponse:
    products = [
        ProductResult(
            id=r["id"],
            score=r["score"],
            **{k: r["payload"].get(k) for k in ProductResult.model_fields if k not in ("id", "score")},
        )
        for r in raw_results
    ]
    return SearchResponse(query_type=query_type, results=products, total=len(products))
