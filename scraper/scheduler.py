"""
scraper/scheduler.py
APScheduler setup — runs scraping jobs and maintenance jobs on cron schedules.
Each site runs as an independent job so failures are isolated.
"""
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler

from backend.config import settings
from backend.utils.logger import get_logger
from scraper.executor import TARGET_SITES, run_site
from jobs.dead_link_checker import check_dead_links
from jobs.config_invalidator import check_stale_configs

logger = get_logger(__name__)
scheduler = BackgroundScheduler()


def _run_async(coro):
    """Helper to run async functions from a sync APScheduler job."""
    asyncio.run(coro)


def start_scheduler() -> None:
    """Register all scheduled jobs and start the scheduler."""
    interval_hours = settings.scrape_interval_hours

    # ── Scrape jobs: one per site, offset by 10 min each ──
    for i, site in enumerate(TARGET_SITES):
        scheduler.add_job(
            _run_async,
            "interval",
            hours=interval_hours,
            args=[run_site(site)],
            id=f"scrape_{site}",
            name=f"Scrape {site}",
            misfire_grace_time=3600,
        )
        logger.info("Scheduled scrape job for %s every %dh", site, interval_hours)

    # ── Dead link checker: every 24h ──
    scheduler.add_job(
        _run_async,
        "interval",
        hours=settings.dead_link_check_interval_hours,
        args=[check_dead_links()],
        id="dead_link_checker",
        name="Dead Link Checker",
    )

    # ── Config invalidator: every 24h ──
    scheduler.add_job(
        check_stale_configs,
        "interval",
        hours=24,
        id="config_invalidator",
        name="Stale Config Invalidator",
    )

    scheduler.start()
    logger.info("Scheduler started.")
