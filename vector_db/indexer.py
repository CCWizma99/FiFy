"""
vector_db/indexer.py
Upserts product points into Qdrant.
Each product gets both an image and text vector stored as named vectors.
"""
import uuid

from qdrant_client.models import PointStruct

from embeddings.image_embedder import embed_image
from embeddings.text_embedder import embed_text
from vector_db.client import get_client
from backend.config import settings
from backend.utils.logger import get_logger

import httpx
from PIL import Image
import io

logger = get_logger(__name__)


async def upsert_product(product: dict) -> str:
    """
    Generate CLIP embeddings for a validated product and upsert into Qdrant.
    Returns the UUID assigned to the product.
    """
    # Download image into memory
    image_vector = await _get_image_vector(product["image_url"])
    text_input = f"{product.get('product_name', '')} {product.get('category', '')}".strip()
    text_vector = embed_text(text_input)

    product_id = str(uuid.uuid4())
    payload = {k: v for k, v in product.items() if k not in ("price",)}
    payload["price"] = float(product.get("price", 0))

    client = get_client()
    client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            PointStruct(
                id=product_id,
                vector={"image": image_vector, "text": text_vector},
                payload=payload,
            )
        ],
    )
    logger.debug("Upserted product %s (%s)", product_id, product.get("product_name"))
    return product_id


async def _get_image_vector(image_url: str) -> list[float]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(image_url, follow_redirects=True)
        resp.raise_for_status()
    image = Image.open(io.BytesIO(resp.content)).convert("RGB")
    return embed_image(image)
