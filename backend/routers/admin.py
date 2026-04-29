"""
backend/routers/admin.py
POST /admin/scrape/trigger — manually trigger a scrape job
GET  /admin/scrape/status  — list recent scrape job records
"""
from fastapi import APIRouter
from typing import List

from backend.database import get_connection
from backend.models.job import ScrapeJobStatus, ScrapeJobsResponse, ScraperStats, DeadLetterEntry, TargetSite
from scraper.pipeline.dead_letter import load_dead_letters
from backend.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


import threading
import asyncio
import sys
import traceback

def run_scraper_in_thread(site: str):
    """Worker function to run the async scraper in a dedicated thread with its own loop."""
    try:
        # Emergency console print in case logger is broken
        print(f"DEBUG: Scraper thread for {site} is actually starting...")
        
        logger.info(f"--- THREAD START: Scraper worker for {site} ---")
        
        if sys.platform == 'win32':
            logger.info("Worker: Forcing Windows ProactorEventLoopPolicy...")
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        logger.info("Worker: Creating fresh event loop...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            from scraper.executor import run_site
            logger.info(f"Worker: Calling run_site({site})…")
            loop.run_until_complete(run_site(site))
            logger.info(f"Worker: Scrape job finished for {site}")
        except Exception as e:
            logger.error(f"Worker ERROR during run_site: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            logger.info("Worker: Closing event loop...")
            loop.close()
            
    except Exception as e:
        # This catches errors that happen BEFORE the loop is even created
        msg = f"CRITICAL THREAD INITIALIZATION FAILURE: {str(e)}\n{traceback.format_exc()}"
        print(msg)
        logger.critical(msg)

@router.post("/scrape/trigger")
async def trigger_scrape(site: str):
    """Manually kick off a scrape job for a given site."""
    logger.info(f"API: Received trigger request for {site}")
    
    with get_connection() as conn:
        row = conn.execute("SELECT domain FROM target_sites WHERE domain = ?", (site,)).fetchone()
    
    if not row:
        logger.warning(f"API: Rejecting trigger for unknown site {site}")
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Unknown site '{site}'. Please add it to Target Sites first.",
        )

    logger.info(f"API: Spawning background thread for {site}...")
    try:
        thread = threading.Thread(target=run_scraper_in_thread, args=(site,), daemon=True)
        thread.start()
        logger.info(f"API: Thread spawned successfully for {site}")
    except Exception as e:
        logger.error(f"API: Failed to spawn thread: {e}")
        return {"error": str(e)}
    
    return {"message": f"Scrape job triggered for {site} in background thread.", "site": site}


@router.get("/sites", response_model=List[TargetSite])
async def get_sites():
    """Return all configured target sites."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM target_sites").fetchall()
    return [TargetSite(**dict(row)) for row in rows]


@router.post("/sites", response_model=TargetSite)
async def add_site(site: TargetSite):
    """Add a new target site to the registry."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO target_sites (domain, listing_url, is_active) VALUES (?, ?, ?)",
            (site.domain, site.listing_url, 1 if site.is_active else 0)
        )
        conn.commit()
    return site


@router.get("/scrape/status", response_model=ScrapeJobsResponse)
async def scrape_status(limit: int = 20):
    """Return the most recent scrape job records."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM scrape_jobs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    jobs = [ScrapeJobStatus(**dict(row)) for row in rows]
    return ScrapeJobsResponse(jobs=jobs)


@router.get("/stats", response_model=ScraperStats)
async def get_stats():
    """Return aggregated scraper stats."""
    with get_connection() as conn:
        # Total products
        res = conn.execute("SELECT COUNT(*) as total, SUM(is_active) as active FROM url_hashes").fetchone()
        total_products = res["total"] or 0
        active_products = res["active"] or 0

        # Job stats
        res = conn.execute("SELECT COUNT(*) as count FROM scrape_jobs").fetchone()
        total_jobs = res["count"] or 0

        # Success rate (last 50 jobs)
        rows = conn.execute(
            "SELECT status FROM scrape_jobs ORDER BY id DESC LIMIT 50"
        ).fetchall()
        if rows:
            successes = sum(1 for r in rows if r["status"] == "completed")
            success_rate = round((successes / len(rows)) * 100, 1)
        else:
            success_rate = 0.0

    # Dead letter count
    dead_letters = load_dead_letters()
    
    return ScraperStats(
        total_products=total_products,
        active_products=active_products,
        total_jobs=total_jobs,
        success_rate=success_rate,
        failed_products_count=len(dead_letters)
    )


@router.get("/dead-letters", response_model=List[DeadLetterEntry])
async def get_dead_letters(limit: int = 50):
    """Return recent dead letter log entries."""
    entries = load_dead_letters()
    return entries[-limit:][::-1]  # Last 'limit' entries, reversed (newest first)
