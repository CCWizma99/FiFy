"""
vector_db/schema.py
Qdrant collection creation with named vectors (image + text).
Run once to initialise the collection before first scrape.
"""
from qdrant_client.models import Distance, VectorParams, VectorsConfig

from vector_db.client import get_client
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

VECTOR_DIM = 512  # CLIP ViT-B/32 output dimension


def create_collection(recreate: bool = False) -> None:
    """
    Create the Qdrant collection with named vectors for image and text embeddings.
    Set recreate=True to drop and recreate (WARNING: deletes all data).
    """
    client = get_client()
    collection = settings.qdrant_collection

    if recreate:
        client.delete_collection(collection)
        logger.warning("Dropped existing collection '%s'", collection)

    existing = [c.name for c in client.get_collections().collections]
    if collection in existing:
        logger.info("Collection '%s' already exists — skipping creation.", collection)
        return

    client.create_collection(
        collection_name=collection,
        vectors_config={
            "image": VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            "text":  VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        }
    )
    logger.info("Created Qdrant collection '%s' with image+text named vectors.", collection)

    # Add payload indexes for filtering
    client.create_payload_index(collection, field_name="category", field_schema="keyword")
    client.create_payload_index(collection, field_name="gender", field_schema="keyword")
    client.create_payload_index(collection, field_name="price", field_schema="float")
    logger.info("Created payload indexes for 'category', 'gender', and 'price'.")
