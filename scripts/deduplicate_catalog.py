"""
scripts/deduplicate_catalog.py
Surgical cleanup script to remove duplicate products and "junk" images (MintPay/Logos).
"""
import os
import sys
import json
import hashlib
from collections import defaultdict

# Add project root to path
sys.path.append(os.getcwd())

from vector_db.client import get_client
from backend.config import settings
from backend.database import get_connection
from backend.utils.logger import get_logger

logger = get_logger("deduplicator")

JUNK_KEYWORDS = ["logo", "icon", "banner", "pixel", "loading", "spinner", "placeholder", "badge", "mintpay", "appstore", "playstore"]

def get_product_fingerprint(payload):
    """Generate a semantic fingerprint for a product."""
    name = str(payload.get("product_name", "")).strip().lower()
    price = str(payload.get("price", "")).strip()
    site = payload.get("source_site", "")
    return f"{site}|{name}|{price}"

def is_junk_image(url):
    """Check if the image URL contains junk keywords."""
    if not url: return True
    url_lower = url.lower()
    return any(k in url_lower for k in JUNK_KEYWORDS)

async def run_deduplication():
    client = get_client()
    collection = settings.qdrant_collection
    
    logger.info(f"Starting deduplication for collection: {collection}")
    
    groups = defaultdict(list)
    total_scanned = 0
    
    # 1. Scroll through all points in Qdrant
    offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=collection,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        for p in points:
            total_scanned += 1
            fingerprint = get_product_fingerprint(p.payload)
            groups[fingerprint].append({
                "id": p.id,
                "url": p.payload.get("product_url"),
                "image_url": p.payload.get("image_url"),
                "name": p.payload.get("product_name")
            })
            
        offset = next_offset
        if not offset:
            break
            
    logger.info(f"Scanned {total_scanned} products. Found {len(groups)} unique identities.")
    
    ids_to_delete = []
    urls_to_purge_from_sql = []
    
    # 2. Analyze groups for duplicates and junk
    for fingerprint, members in groups.items():
        if len(members) == 1:
            # Check if even the single entry is junk
            if is_junk_image(members[0]["image_url"]):
                logger.info(f"Marking single junk entry for deletion: {members[0]['name']} ({members[0]['image_url']})")
                ids_to_delete.append(members[0]["id"])
                urls_to_purge_from_sql.append(members[0]["url"])
            continue
            
        # We have duplicates!
        # Sort members: prioritize clean images over junk images
        members.sort(key=lambda x: is_junk_image(x["image_url"]))
        
        # Keep the first one (the cleanest one)
        keep = members[0]
        to_kill = members[1:]
        
        logger.info(f"Found {len(members)} duplicates for '{keep['name']}'. Keeping {keep['id']}, deleting {len(to_kill)} others.")
        
        for m in to_kill:
            ids_to_delete.append(m["id"])
            urls_to_purge_from_sql.append(m["url"])
            
        # If the one we kept is STILL junk, mark it too (better to have nothing than a logo)
        if is_junk_image(keep["image_url"]):
            logger.warning(f"Even the 'best' version of '{keep['name']}' has a junk image. Deleting all versions.")
            ids_to_delete.append(keep["id"])
            urls_to_purge_from_sql.append(keep["url"])

    # 3. Execute Deletions in Qdrant
    if ids_to_delete:
        logger.info(f"Deleting {len(ids_to_delete)} duplicate/junk points from Qdrant...")
        # Qdrant delete is immediate
        client.delete(
            collection_name=collection,
            points_selector=ids_to_delete
        )
        
        # 4. Clear SQL registry so they can be re-crawled correctly if needed
        logger.info(f"Cleaning SQL deduplication registry for {len(urls_to_purge_from_sql)} URLs...")
        with get_connection() as conn:
            # We use batches for SQL deletion to avoid locking
            for i in range(0, len(urls_to_purge_from_sql), 100):
                batch = urls_to_purge_from_sql[i:i+100]
                placeholders = ",".join(["?"] * len(batch))
                conn.execute(f"DELETE FROM url_hashes WHERE url IN ({placeholders})", batch)
            conn.commit()
            
        logger.info("Cleanup complete.")
    else:
        logger.info("No duplicates or junk images found.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_deduplication())
