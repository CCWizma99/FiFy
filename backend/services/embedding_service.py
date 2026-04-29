"""
backend/services/embedding_service.py
Thin wrapper over the CLIP embedding engine (embeddings/).
The backend calls these functions; the actual model lives in embeddings/.
"""
import io
from PIL import Image

from embeddings.image_embedder import embed_image
from embeddings.text_embedder import embed_text


async def get_image_embedding(image_bytes: bytes) -> list[float]:
    """Convert raw image bytes to a 512-dim CLIP vector."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return embed_image(image)


async def get_text_embedding(text: str) -> list[float]:
    """Convert a text string to a 512-dim CLIP vector."""
    return embed_text(text)
