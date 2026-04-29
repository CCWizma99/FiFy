"""
vector_db/searcher.py
Cosine similarity search against a named vector in Qdrant.
Supports payload filters for category, gender, price range.
"""
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

from vector_db.client import get_client
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def search_by_vector(
    collection: str,
    vector: list[float],
    vector_name: str,
    filters: dict,
    limit: int = 20,
) -> list[dict]:
    """
    Run a named-vector similarity search.
    Returns a list of dicts: {id, score, payload}.
    """
    client = get_client()
    qdrant_filter = _build_filter(filters)

    results = client.search(
        collection_name=collection,
        query_vector=(vector_name, vector),
        query_filter=qdrant_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    return [
        {"id": str(r.id), "score": r.score, "payload": r.payload}
        for r in results
    ]


def _build_filter(filters: dict) -> Filter | None:
    if not filters:
        return None

    conditions = []

    if "category" in filters:
        conditions.append(FieldCondition(key="category", match=MatchValue(value=filters["category"])))
    if "gender" in filters:
        conditions.append(FieldCondition(key="gender", match=MatchValue(value=filters["gender"])))
    if "min_price" in filters or "max_price" in filters:
        conditions.append(
            FieldCondition(
                key="price",
                range=Range(
                    gte=filters.get("min_price"),
                    lte=filters.get("max_price"),
                ),
            )
        )

    return Filter(must=conditions) if conditions else None
