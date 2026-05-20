from vector_db.client import get_client
from backend.config import settings

client = get_client()
points, _ = client.scroll(
    collection_name=settings.qdrant_collection,
    limit=5,
    with_payload=True,
    with_vectors=False
)

for p in points:
    print(f"ID: {p.id}, Payload: {p.payload}")
