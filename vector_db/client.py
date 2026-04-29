"""
vector_db/client.py
Qdrant client singleton — created once and reused across all operations.
"""
from qdrant_client import QdrantClient
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        logger.info("Connecting to Qdrant at %s", settings.qdrant_url)
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
        logger.info("Qdrant client connected.")
    return _client
