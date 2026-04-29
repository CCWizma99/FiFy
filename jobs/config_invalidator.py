"""
jobs/config_invalidator.py
Checks if any site's scraper config has gone stale.
If a site returns zero products on 3 consecutive runs, the config is flagged
as stale and the Site Analyzer Agent is re-triggered to regenerate it.
"""
from pathlib import Path

from backend.database import get_connection
from backend.utils.logger import get_logger

logger = get_logger(__name__)
CONSECUTIVE_FAIL_THRESHOLD = 3
CONFIGS_DIR = Path("scraper/configs")


def check_stale_configs() -> None:
    logger.info("Config invalidator: checking for stale scraper configs…")
    with get_connection() as conn:
        sites = conn.execute("SELECT DISTINCT site FROM scrape_jobs").fetchall()

    for row in sites:
        site = row["site"]
        recent_jobs = _get_recent_jobs(site, limit=CONSECUTIVE_FAIL_THRESHOLD)

        if len(recent_jobs) >= CONSECUTIVE_FAIL_THRESHOLD:
            all_zero = all(j["products_scraped"] == 0 and j["status"] == "completed" for j in recent_jobs)
            if all_zero:
                logger.warning(
                    "Site %s returned 0 products for %d consecutive runs — invalidating config.",
                    site, CONSECUTIVE_FAIL_THRESHOLD
                )
                _invalidate_config(site)


def _get_recent_jobs(site: str, limit: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT products_scraped, status FROM scrape_jobs WHERE site=? ORDER BY id DESC LIMIT ?",
            (site, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def _invalidate_config(site: str) -> None:
    """Delete the cached config file so it gets regenerated on the next scrape."""
    config_path = CONFIGS_DIR / f"{site.replace('.', '_')}.json"
    if config_path.exists():
        config_path.unlink()
        logger.info("Deleted stale config for %s — will be regenerated on next scrape.", site)
