"""
backend/routers/admin.py
POST /admin/scrape/trigger — manually trigger a scrape job
GET  /admin/scrape/status  — list recent scrape job records
"""
from fastapi import APIRouter, BackgroundTasks

from backend.database import get_connection
from backend.models.job import ScrapeJobStatus, ScrapeJobsResponse

router = APIRouter()

VALID_SITES = ["asos.com", "zara.com", "hm.com", "uniqlo.com", "zalando.com"]


@router.post("/scrape/trigger")
async def trigger_scrape(site: str, background_tasks: BackgroundTasks):
    """Manually kick off a scrape job for a given site."""
    if site not in VALID_SITES:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Unknown site '{site}'. Valid sites: {VALID_SITES}",
        )

    # Lazy import to avoid circular deps; scraper runs in background thread
    from scraper.executor import run_site
    background_tasks.add_task(run_site, site)
    return {"message": f"Scrape job triggered for {site}.", "site": site}


@router.get("/scrape/status", response_model=ScrapeJobsResponse)
async def scrape_status(limit: int = 20):
    """Return the most recent scrape job records."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM scrape_jobs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    jobs = [ScrapeJobStatus(**dict(row)) for row in rows]
    return ScrapeJobsResponse(jobs=jobs)
