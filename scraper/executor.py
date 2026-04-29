"""
scraper/executor.py
Playwright-based scraper executor.
For each target site:
  1. Load (or generate) the scraping config
  2. Navigate listing pages via Playwright
  3. Extract raw product data
  4. Validate each product
  5. Generate CLIP embeddings
  6. Store in Qdrant

Images are downloaded into memory only — never written to disk.
"""
import asyncio
import hashlib
from datetime import datetime, timezone

from playwright.async_api import async_playwright

from backend.database import get_connection
from backend.utils.logger import get_logger
from scraper.pipeline.validator import validate_product, ValidationError
from scraper.site_analyzer.agent import analyze_site, load_config
from vector_db.indexer import upsert_product

logger = get_logger(__name__)

TARGET_SITES = {
    "asos.com":     "https://www.asos.com/women/dresses/cat/?cid=8799",
    "zara.com":     "https://www.zara.com/us/en/woman-dresses-l1066.html",
    "hm.com":       "https://www2.hm.com/en_us/women/products/dresses.html",
    "uniqlo.com":   "https://www.uniqlo.com/us/en/women/dresses",
    "zalando.com":  "https://www.zalando.co.uk/womens-clothing-dresses/",
}


async def run_site(site_domain: str) -> None:
    """Entry point for scraping a single site. Called by scheduler or admin endpoint."""
    logger.info("Starting scrape for %s", site_domain)
    job_id = _start_job(site_domain)

    try:
        config = load_config(site_domain)
        if not config:
            logger.info("No cached config for %s — running Site Analyzer Agent", site_domain)
            listing_url = TARGET_SITES[site_domain]
            listing_html, detail_html = await _fetch_html_samples(listing_url)
            config = analyze_site(site_domain, listing_html, detail_html)

        count = await _scrape_with_config(config, site_domain)
        _finish_job(job_id, count)
        logger.info("Scrape complete for %s — %d products processed", site_domain, count)

    except Exception as e:
        _fail_job(job_id, str(e))
        logger.error("Scrape failed for %s: %s", site_domain, e)
        raise


async def _fetch_html_samples(listing_url: str) -> tuple[str, str]:
    """Fetch listing page HTML and a sample product detail page HTML."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(listing_url, wait_until="networkidle", timeout=30_000)
        listing_html = await page.content()

        # Click first product link to get detail HTML
        first_link = await page.query_selector("a[href*='product'], a[href*='item']")
        detail_html = ""
        if first_link:
            async with page.expect_navigation():
                await first_link.click()
            detail_html = await page.content()

        await browser.close()
    return listing_html, detail_html


async def _scrape_with_config(config: dict, site_domain: str) -> int:
    """Navigate paginated listing pages using the config and process each product."""
    count = 0
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        listing_url = config.get("listing_url_pattern", TARGET_SITES[site_domain])
        await page.goto(listing_url, wait_until="networkidle", timeout=30_000)

        while True:
            cards = await page.query_selector_all(config["product_card_selector"])
            for card in cards:
                product = await _extract_product(card, config, site_domain)
                if product and not _already_scraped(product):
                    try:
                        validated = await validate_product(product, site_domain)
                        await upsert_product(validated)
                        _register_hash(validated)
                        count += 1
                    except ValidationError:
                        pass  # Logged inside validator

            # Pagination
            next_btn = await page.query_selector(config.get("pagination_selector", ""))
            if not next_btn:
                break
            await next_btn.click()
            await page.wait_for_load_state("networkidle")

        await browser.close()
    return count


async def _extract_product(card, config: dict, site_domain: str) -> dict | None:
    """Extract raw product fields from a Playwright element using config selectors."""
    fields = config.get("fields", {})
    try:
        name_el = await card.query_selector(fields.get("name", ""))
        price_el = await card.query_selector(fields.get("price", ""))
        img_el = await card.query_selector(fields.get("image_url", ""))
        url_el = await card.query_selector(fields.get("product_url", ""))

        return {
            "product_name": (await name_el.inner_text()).strip() if name_el else "",
            "price": (await price_el.inner_text()).strip() if price_el else "",
            "image_url": (await img_el.get_attribute("src") or await img_el.get_attribute("data-src") or "") if img_el else "",
            "product_url": (await url_el.get_attribute("href") or "") if url_el else "",
            "source_site": site_domain,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }
    except Exception as e:
        logger.debug("Failed to extract product card: %s", e)
        return None


def _already_scraped(product: dict) -> bool:
    url_hash = hashlib.md5(product["product_url"].encode()).hexdigest()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT hash FROM url_hashes WHERE url = ?", (product["product_url"],)
        ).fetchone()
    return row is not None and row["hash"] == url_hash


def _register_hash(product: dict) -> None:
    url_hash = hashlib.md5(product["product_url"].encode()).hexdigest()
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO url_hashes (url, hash, last_seen) VALUES (?, ?, ?)",
            (product["product_url"], url_hash, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def _start_job(site: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO scrape_jobs (site, started_at, status) VALUES (?, ?, 'running')",
            (site, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def _finish_job(job_id: int, count: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE scrape_jobs SET finished_at=?, status='completed', products_scraped=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), count, job_id),
        )
        conn.commit()


def _fail_job(job_id: int, error: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE scrape_jobs SET finished_at=?, status='failed', error_message=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), error, job_id),
        )
        conn.commit()
