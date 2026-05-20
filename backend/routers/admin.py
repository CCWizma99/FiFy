from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.database import get_connection
from backend.services.crawl_manager import crawl_manager
import asyncio
import json

router = APIRouter()

class SiteBase(BaseModel):
    domain: str
    root_url: str

class SiteResponse(SiteBase):
    id: int
    is_active: bool
    status: str
    last_crawl_at: Optional[str]
    total_products: int

@router.get("/sites", response_model=List[SiteResponse])
async def get_sites():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM sites").fetchall()
        return [dict(row) for row in rows]

@router.post("/sites", response_model=SiteResponse)
async def add_site(site: SiteBase):
    with get_connection() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO sites (domain, root_url) VALUES (?, ?)",
                (site.domain, site.root_url)
            )
            conn.commit()
            row = conn.execute("SELECT * FROM sites WHERE id = ?", (cur.lastrowid,)).fetchone()
            return dict(row)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@router.put("/sites/{site_id}", response_model=SiteResponse)
async def update_site(site_id: int, site: SiteBase):
    with get_connection() as conn:
        try:
            conn.execute(
                "UPDATE sites SET domain = ?, root_url = ? WHERE id = ?",
                (site.domain, site.root_url, site_id)
            )
            conn.commit()
            row = conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Site not found")
            return dict(row)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@router.post("/sites/{site_id}/start")
async def start_crawl(site_id: int):
    await crawl_manager.start_crawl(site_id)
    return {"status": "started"}

@router.post("/sites/{site_id}/pause")
async def pause_crawl(site_id: int):
    crawl_manager.pause_crawl(site_id)
    return {"status": "paused"}

@router.post("/sites/{site_id}/resume")
async def resume_crawl(site_id: int):
    crawl_manager.resume_crawl(site_id)
    return {"status": "resumed"}

@router.post("/sites/{site_id}/stop")
async def stop_crawl(site_id: int):
    crawl_manager.stop_crawl(site_id)
    return {"status": "stopped"}

@router.delete("/sites/{site_id}")
async def delete_site(site_id: int):
    from vector_db.client import get_client
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    from backend.config import settings

    with get_connection() as conn:
        site = conn.execute("SELECT domain FROM sites WHERE id = ?", (site_id,)).fetchone()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        
        domain = site["domain"]

        # 1. Delete from Qdrant
        try:
            client = get_client()
            client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=Filter(
                    must=[FieldCondition(key="source_site", match=MatchValue(value=domain))]
                )
            )
        except Exception as e:
            print(f"Warning: Failed to delete from Qdrant: {e}")

        # 2. Delete from DB tables (Cascading manually since we don't have FK constraints everywhere)
        conn.execute("DELETE FROM url_hashes WHERE url IN (SELECT url FROM url_hashes WHERE url LIKE ?)", (f"%{domain}%",))
        conn.execute("DELETE FROM crawl_queue WHERE site_id = ?", (site_id,))
        conn.execute("DELETE FROM indexing_stats WHERE site_id = ?", (site_id,))
        conn.execute("DELETE FROM scrape_jobs WHERE site = ?", (domain,))
        conn.execute("DELETE FROM sites WHERE id = ?", (site_id,))
        conn.commit()

    return {"status": "deleted"}

@router.post("/sites/{site_id}/reset")
async def reset_site(site_id: int):
    from vector_db.client import get_client
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    from backend.config import settings
    import os
    from pathlib import Path

    with get_connection() as conn:
        site = conn.execute("SELECT domain FROM sites WHERE id = ?", (site_id,)).fetchone()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        
        domain = site["domain"]

        # 1. Stop active spider
        crawl_manager.stop_crawl(site_id)

        # 2. Delete from Qdrant
        try:
            client = get_client()
            client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=Filter(
                    must=[FieldCondition(key="source_site", match=MatchValue(value=domain))]
                )
            )
        except Exception as e:
            print(f"Warning: Failed to delete from Qdrant during reset: {e}")

        # 3. Clear DB memory (queue, hashes, stats, jobs)
        conn.execute("DELETE FROM crawl_queue WHERE site_id = ?", (site_id,))
        # Precise cleanup using the new site_domain column
        conn.execute("DELETE FROM url_hashes WHERE site_domain = ?", (domain,))
        conn.execute("DELETE FROM indexing_stats WHERE site_id = ?", (site_id,))
        conn.execute("DELETE FROM scrape_jobs WHERE site = ?", (domain,))
        
        # 4. Clear Dead Letter Log for this site
        dead_letter_path = Path("data/dead_letter.log")
        if dead_letter_path.exists():
            try:
                with open(dead_letter_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                with open(dead_letter_path, "w", encoding="utf-8") as f:
                    for line in lines:
                        try:
                            data = json.loads(line)
                            if data.get("source_site") != domain:
                                f.write(line)
                        except:
                            f.write(line)
            except Exception as e:
                print(f"Warning: Failed to clear dead letter log: {e}")
        
        # 5. Reset site counters
        conn.execute("""
            UPDATE sites SET 
                total_products = 0, 
                status = 'idle', 
                last_crawl_at = NULL 
            WHERE id = ?
        """, (site_id,))
        conn.commit()

        # 5. Delete AI configuration file
        config_path = Path("scraper/configs") / f"{domain.replace('.', '_')}.json"
        if not config_path.exists():
            # Fallback for standard domain names
            config_path = Path("scraper/configs") / f"{domain}.json"
            
        if config_path.exists():
            try:
                os.remove(config_path)
            except Exception as e:
                print(f"Warning: Failed to delete config file: {e}")

    return {"status": "site_reset_complete", "site": domain}

@router.get("/stats")
async def get_stats():
    with get_connection() as conn:
        total_products = conn.execute("SELECT SUM(total_products) FROM sites").fetchone()[0] or 0
        active_products = conn.execute("SELECT COUNT(*) FROM url_hashes WHERE is_active = 1").fetchone()[0]
        total_jobs = conn.execute("SELECT COUNT(*) FROM scrape_jobs").fetchone()[0]
        success_rate = 100 # Placeholder
        from backend.services.system_status import system_status
        return {
            "total_products": total_products,
            "active_products": active_products,
            "total_jobs": total_jobs,
            "success_rate": success_rate,
            "failed_products_count": 0,
            "quota_status": system_status.get_quota_status()
        }

@router.get("/stats/categories")
async def get_category_stats():
    from vector_db.client import get_client
    from qdrant_client.models import Filter
    from backend.config import settings
    
    client = get_client()
    # This is a bit expensive in Qdrant if we don't have indexes, 
    # but for an admin dash it's okay for now.
    # In production, we'd store these counters in SQLite.
    
    # For now, let's just return some dummy stats or do a scroll/count
    # Actually, let's just use SQLite stats if we had them.
    # We don't have category stats in SQLite yet.
    
    # Simple implementation: return a static list for UI testing or try to count
    return [
        {"name": "Clothing", "count": 120},
        {"name": "Shoes", "count": 45},
        {"name": "Bags", "count": 30},
        {"name": "Accessories", "count": 60},
        {"name": "Other", "count": 12},
    ]

@router.get("/scrape/status")
async def get_scrape_status(limit: int = 10):
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM scrape_jobs ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
        return {"jobs": [dict(row) for row in rows]}

@router.get("/dead-letters")
async def get_dead_letters(limit: int = 20):
    # Placeholder: currently we don't have a dead_letters table, 
    # but the frontend expects an array.
    return []

@router.post("/reset")
async def reset_all_data():
    from vector_db.client import get_client
    from backend.config import settings
    from qdrant_client.models import Filter

    # 1. Clear Qdrant
    try:
        client = get_client()
        # Delete all points in the collection
        # We can also recreate the collection, but delete by filter is safer if collection config is complex
        client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=Filter() # Empty filter matches all
        )
    except Exception as e:
        print(f"Warning: Failed to clear Qdrant: {e}")

    # 2. Clear DB tables
    with get_connection() as conn:
        conn.execute("DELETE FROM url_hashes")
        conn.execute("DELETE FROM crawl_queue")
        conn.execute("DELETE FROM indexing_stats")
        conn.execute("DELETE FROM scrape_jobs")
        conn.execute("DELETE FROM sites")
        conn.commit()

    return {"status": "reset_complete"}
    
@router.post("/categorize/clear-quota")
async def clear_quota_error():
    from backend.services.system_status import system_status
    system_status.clear_quota_error()
    return {"status": "cleared"}

@router.post("/categorize/run")
async def trigger_categorization(limit: int = 300):
    """Trigger the batch AI categorization job."""
    from scraper.batch_categorizer import run_batch_categorization
    # Run in background to avoid timeout
    asyncio.create_task(run_batch_categorization(limit))
    return {"status": "categorization_started", "limit": limit}

@router.websocket("/ws/logs/{site_id}")
async def websocket_endpoint(websocket: WebSocket, site_id: int):
    await websocket.accept()
    queue = await crawl_manager.subscribe_logs(site_id)
    try:
        while True:
            data = await queue.get()
            await websocket.send_text(data)
    except WebSocketDisconnect:
        crawl_manager.unsubscribe_logs(site_id, queue)
    except Exception:
        crawl_manager.unsubscribe_logs(site_id, queue)
