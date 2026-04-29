"""
backend/services/qdrant_service.py
Qdrant client wrapper used by the backend layer.
Delegates to vector_db/ for actual Qdrant operations.
"""
from typing import Optional

from vector_db.searcher import search_by_vector, build_filter
from vector_db.client import get_client
from backend.config import settings


async def query_similar_products(
    vector: list[float],
    vector_name: str,
    filters: dict,
    limit: int = None,
) -> list[dict]:
    """
    Run a named-vector similarity search against Qdrant.
    Returns a list of product payload dicts with scores attached.
    """
    limit = limit or settings.max_results
    results = search_by_vector(
        collection=settings.qdrant_collection,
        vector=vector,
        vector_name=vector_name,
        filters=filters,
        limit=limit,
    )
    return results


async def get_product_by_id(product_id: str) -> Optional[dict]:
    """Fetch a single product point from Qdrant by UUID."""
    client = get_client()
    results = client.retrieve(
        collection_name=settings.qdrant_collection,
        ids=[product_id],
        with_payload=True,
        with_vectors=False,
    )
    if not results:
        return None
    return results[0].payload


async def list_products(limit: int = 10, filters: dict = None) -> list[dict]:
    """Fetch a list of products (scroll) from Qdrant with optional filtering."""
    client = get_client()
    qdrant_filter = build_filter(filters) if filters else None
    
    # Using scroll to get latest or arbitrary points
    points, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=qdrant_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    return [p.payload for p in points]
