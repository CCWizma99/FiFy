from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
from vector_db.client import get_client
from backend.utils.logger import get_logger

logger = get_logger(__name__)

def search_by_vector(collection, vector, vector_name, filters, limit=20):
    client = get_client()
    q_filter = build_filter(filters)
    res = client.query_points(
        collection_name=collection,
        query=vector,
        using=vector_name,
        query_filter=q_filter,
        limit=limit,
        with_payload=True,
    )
    return [{"id": str(r.id), "score": r.score, "payload": r.payload} for r in res.points]

def build_filter(filters):
    if not filters: return None
    cond = []
    if filters.get("category"):
        cond.append(FieldCondition(key="category", match=MatchValue(value=filters["category"])))
    if filters.get("gender"):
        cond.append(FieldCondition(key="gender", match=MatchValue(value=filters["gender"])))
    if filters.get("min_price") is not None or filters.get("max_price") is not None:
        cond.append(FieldCondition(key="price", range=Range(gte=filters.get("min_price"), lte=filters.get("max_price"))))
    return Filter(must=cond) if cond else None
