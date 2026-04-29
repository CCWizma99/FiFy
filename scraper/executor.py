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
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

from backend.database import get_connection
from backend.utils.logger import get_logger
from scraper.pipeline.validator import validate_product, ValidationError
from scraper.site_analyzer.agent import analyze_site, load_config
from vector_db.indexer import upsert_product

logger = get_logger(__name__)

async def run_site(site_domain: str) -> None:
    """Entry point for scraping a single site. Called by scheduler or admin endpoint."""
    logger.info("Starting scrape for %s", site_domain)
    job_id = _start_job(site_domain)

    try:
        # Fetch listing URL from DB
        with get_connection() as conn:
            row = conn.execute("SELECT listing_url FROM target_sites WHERE domain = ?", (site_domain,)).fetchone()
        
        if not row:
            raise ValueError(f"Site {site_domain} not found in target_sites registry")
        
        listing_url = row["listing_url"]
        
        # Always re-run card discovery on every trigger — selectors may have changed.
        cached = load_config(site_domain)
        analysis_url = listing_url
        if cached and cached.get("listing_url_pattern"):
            analysis_url = cached["listing_url_pattern"]
            logger.info("Trying cached listing_url_pattern: %s", analysis_url)

        logger.info("Running card discovery for %s...", site_domain)
        listing_html, detail_html, card_html, confirmed_url = await _fetch_html_samples(analysis_url)
        
        # FALLBACK: If discovery failed on the cached URL, try again from the base URL
        if not card_html and analysis_url != listing_url:
            logger.warning("Discovery failed on cached URL %s. Reverting to base URL %s", analysis_url, listing_url)
            listing_html, detail_html, card_html, confirmed_url = await _fetch_html_samples(listing_url)

        if not card_html:
            raise ValueError(f"Could not find any product cards for {site_domain} even after fallback.")

        config = analyze_site(site_domain, listing_html, detail_html, card_html, confirmed_listing_url=confirmed_url)

        count = await _scrape_with_config(config, site_domain, listing_url)
        _finish_job(job_id, count)
        logger.info("Scrape complete for %s — %d products processed", site_domain, count)

    except Exception as e:
        _fail_job(job_id, str(e))
        logger.error("Scrape failed for %s: %s", site_domain, e)
        raise


async def _fetch_html_samples(listing_url: str) -> tuple[str, str, str, str]:
    """Fetch listing page HTML, a sample product detail page HTML, the inner HTML of one product card,
    and the confirmed page URL (the actual URL the browser was on when cards were found)."""
    logger.info(f"Fetching HTML samples from {listing_url}…")
    async with async_playwright() as pw:
        logger.info("Launching browser (Chromium)…")
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        
        logger.info(f"Navigating to: {listing_url}")
        await page.goto(listing_url, wait_until="networkidle", timeout=30_000)
        
        # EXPLORATION: If this looks like a homepage (no clear product grid), try to find a category link
        # Look for "Shop", "Men", "Women", "Category", etc.
        category_link = await page.query_selector("a[href*='shop'], a[href*='category'], a[href*='men'], a[href*='women']")
        if category_link:
            cat_href = await category_link.get_attribute("href")
            # Correctly handle relative URLs like /shop
            target_cat_url = urljoin(listing_url, cat_href)
            
            # Only navigate if it's actually a different page
            if target_cat_url.rstrip("/") != listing_url.rstrip("/"):
                logger.info(f"Discovery: Home page detected. Navigating to potential category: {target_cat_url}")
                try:
                    await page.goto(target_cat_url, wait_until="networkidle", timeout=30000)
                except Exception:
                    logger.warning(f"Discovery: Category navigation failed to {target_cat_url}, staying on current page.")
            else:
                logger.info("Discovery: Already on a valid shop/category page.")

        # Wait for actual products to hydrate in the DOM before capturing HTML
        # This is critical for Next.js sites where the product grid is client-side rendered
        try:
            await page.wait_for_selector("a[href*='product']", timeout=25000)
            logger.info("Product links detected in DOM — page fully hydrated.")
        except Exception:
            logger.warning("Could not confirm product hydration. HTML may be incomplete.")

        listing_html = await page.content()
        logger.info(f"Listing HTML fetched ({len(listing_html)} chars)")

        # Extract card HTML BEFORE navigating away — we are still on the shop/listing page
        card_html = ""
        try:
            # Try direct card containers first, then fall back to traversing from a product link
            for card_selector in ["div.group", "article.product", "li.product", "[class*='product-card']", "[class*='card']"]:
                cards = await page.query_selector_all(card_selector)
                if len(cards) >= 3:  # Need at least 3 to confirm it's a repeating grid, not a one-off
                    # Use outer_html so AI sees the full wrapper element (e.g. <div class="group">)
                    card_html = await cards[0].evaluate("el => el.outerHTML")
                    card_html = card_html[:3000]
                    logger.info(f"Card sample extracted ({len(card_html)} chars) using '{card_selector}'")
                    logger.info(f"--- CARD HTML SAMPLE ---\n{card_html}\n--- END CARD HTML ---")
                    break
            
            # Fallback: traverse from product link to its closest container
            if not card_html:
                links = await page.query_selector_all("a[href*='product']")
                if links:
                    parent_html = await links[0].evaluate(
                        "el => (el.closest('li') || el.closest('article') || el.closest('div[class]') || el.parentElement)?.outerHTML || ''"
                    )
                    if parent_html:
                        card_html = parent_html[:3000]
                        logger.info(f"Card sample extracted via link traversal ({len(card_html)} chars)")
                        logger.info(f"--- CARD HTML SAMPLE ---\n{card_html}\n--- END CARD HTML ---")
        except Exception as e:
            logger.warning(f"Could not extract card sample: {e}")

        # Capture the confirmed listing URL — the actual page.url after discovery/navigation
        # This is used to override whatever URL the AI might hallucinate
        confirmed_url = page.url
        logger.info(f"Confirmed listing URL (page.url after card discovery): {confirmed_url}")

        # NOW navigate to a detail page for extra context
        logger.info("Searching for first product link to get sample detail page…")
        all_links = await page.query_selector_all("a[href*='product']")
        first_link = None
        for link in all_links:
            href = await link.get_attribute("href")
            if href and "product" in href:
                first_link = link
                break

        detail_html = ""
        if first_link:
            href = await first_link.get_attribute("href")
            target_url = urljoin(page.url, href)
            logger.info(f"Found sample product link: {target_url}. Navigating…")
            try:
                await page.goto(target_url, wait_until="networkidle", timeout=30000)
                detail_html = await page.content()
                logger.info(f"Detail HTML fetched ({len(detail_html)} chars)")
            except Exception as e:
                logger.warning(f"Failed to navigate to detail page {target_url}: {e}. Proceeding with listing only.")
        else:
            logger.warning("Could not find a valid product link on the listing page.")

        await browser.close()
        logger.info("Samples fetched and browser closed.")
    return listing_html, detail_html, card_html, confirmed_url


async def _scrape_with_config(config: dict, site_domain: str, listing_url: str) -> int:
    """Navigate paginated listing pages using the config and process each product."""
    count = 0
    logger.info(f"Starting scrape for {site_domain} with generated config.")
    async with async_playwright() as pw:
        logger.info("Launching browser for main scrape…")
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        # Use listing URL from config if present (override), else from DB
        start_url = config.get("listing_url_pattern") or listing_url
        logger.info(f"Navigating to start URL: {start_url}")
        await page.goto(start_url, wait_until="networkidle", timeout=30_000)

        page_num = 1
        while True:
            logger.info(f"Processing listing page {page_num}…")
            
            # Wait for products to hydrate (Next.js renders client-side after networkidle)
            try:
                await page.wait_for_selector("a[href*='product']", timeout=25000)
                logger.info("Product links confirmed in DOM.")
            except Exception:
                logger.warning(f"Timeout waiting for product links on page {page_num}. Trying anyway.")

            # Now wait for the specific card selector from config
            card_selector = config["product_card_selector"]
            try:
                await page.wait_for_selector(card_selector, timeout=10000)
                logger.info(f"Card selector '{card_selector}' found on page.")
            except Exception:
                logger.warning(f"Card selector ({card_selector}) not found on page {page_num}. Saving debug snapshot.")
                debug_path = Path("logs/debug_failure.html")
                debug_path.write_text(await page.content(), encoding="utf-8")
                logger.info(f"Debug HTML saved to {debug_path}")

            cards = await page.query_selector_all(card_selector)
            logger.info(f"Found {len(cards)} product cards on page {page_num}")
            
            page_processed_count = 0
            for i, card in enumerate(cards):
                product = await _extract_product(card, config, site_domain)
                if product:
                    if not _already_scraped(product):
                        try:
                            validated = await validate_product(product, site_domain)
                            await upsert_product(validated)
                            _register_hash(validated)
                            count += 1
                            page_processed_count += 1
                        except ValidationError as ve:
                            logger.debug(f"Product {i} failed validation: {ve}")
                    else:
                        logger.debug(f"Product {i} already scraped, skipping.")
            
            logger.info(f"Finished page {page_num}. Processed {page_processed_count} new products.")

            # Pagination
            pagination_selector = config.get("pagination_selector", "")
            if not pagination_selector:
                logger.info("No pagination selector provided. Stopping.")
                break
                
            next_btn = await page.query_selector(pagination_selector)
            if not next_btn:
                logger.info("Next button not found. Assuming last page.")
                break
                
            logger.info("Clicking next page…")
            try:
                await next_btn.click()
                await page.wait_for_load_state("networkidle", timeout=15000)
                page_num += 1
            except Exception as e:
                logger.warning(f"Pagination failed: {e}. Stopping.")
                break

        await browser.close()
        logger.info(f"Scrape process complete. Total products added: {count}")
    return count


async def _extract_product(card, config: dict, site_domain: str) -> dict | None:
    """Extract raw product fields from a Playwright element using config selectors."""
    fields = config.get("fields", {})
    try:
        name_el = await card.query_selector(fields.get("name", ""))
        price_el = await card.query_selector(fields.get("price", ""))
        img_el = await card.query_selector(fields.get("image_url", ""))
        url_el = await card.query_selector(fields.get("product_url", ""))

        name = (await name_el.inner_text()).strip() if name_el else ""
        price_raw = (await price_el.inner_text()).strip() if price_el else ""
        image = (await img_el.get_attribute("src") or await img_el.get_attribute("data-src") or "") if img_el else ""
        url_raw = (await url_el.get_attribute("href") or "") if url_el else ""

        logger.debug(f"Extracted raw: name={name!r}, price={price_raw!r}, url={url_raw!r}")

        # Resolve relative URLs to absolute
        if image and image.startswith("/"):
            image = f"https://{site_domain}{image}"
        if url_raw and not url_raw.startswith("http"):
            url_raw = f"https://www.{site_domain}{url_raw}" if not url_raw.startswith("//") else f"https:{url_raw}"

        # Clean price: strip currency labels, non-breaking spaces, commas
        price_cleaned = price_raw.replace("LKR", "").replace("\xa0", "").replace(",", "").replace("$", "").strip()

        product = {
            "product_name": name,
            "price": price_cleaned,
            "image_url": image,
            "product_url": url_raw,
            "source_site": site_domain,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }
        return product
    except Exception as e:
        logger.debug("Extraction error on card: %s", e)
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
