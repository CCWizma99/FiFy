"""
jobs/dead_link_checker.py
Runs every 24 hours. Pings the image_url of every active product in Qdrant.
Products returning non-200 get their is_active flag set to false.
Products dead for >7 days are deleted.
"""
from datetime import datetime, timezone, timedelta

import httpx

from vector_db.client import get_client
from backend.config import settings
from backend.utils.logger import get_logger
from qdrant_client.models import FieldCondition, Filter, MatchValue

logger = get_logger(__name__)
DEAD_THRESHOLD_DAYS = 7


async def check_dead_links() -> None:
    logger.info("Dead link checker starting…")
    client = get_client()
    collection = settings.qdrant_collection

    # Scroll all active products
    offset = None
    dead_count = 0
    deleted_count = 0

    while True:
        results, next_offset = client.scroll(
            collection_name=collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="is_active", match=MatchValue(value=True))]
            ),
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        for point in results:
            image_url = point.payload.get("image_url", "")
            if not image_url:
                continue
            is_alive = await _ping_url(image_url)
            if not is_alive:
                scraped_at = point.payload.get("scraped_at", "")
                if _is_expired(scraped_at):
                    client.delete(collection_name=collection, points_selector=[point.id])
                    deleted_count += 1
                    logger.info("Deleted expired dead product %s", point.id)
                else:
                    client.set_payload(
                        collection_name=collection,
                        payload={"is_active": False},
                        points=[point.id],
                    )
                    dead_count += 1

        if next_offset is None:
            break
        offset = next_offset

    logger.info("Dead link check complete. Deactivated: %d | Deleted: %d", dead_count, deleted_count)


async def _ping_url(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.head(url, follow_redirects=True)
        return resp.status_code == 200
    except Exception:
        return False


def _is_expired(scraped_at_iso: str) -> bool:
    try:
        scraped_at = datetime.fromisoformat(scraped_at_iso)
        return datetime.now(timezone.utc) - scraped_at > timedelta(days=DEAD_THRESHOLD_DAYS)
    except Exception:
        return False
