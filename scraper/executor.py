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
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from playwright.async_api import async_playwright

from backend.database import get_connection
from backend.utils.logger import get_logger
from scraper.pipeline.validator import validate_product, ValidationError
from scraper.site_analyzer.agent import analyze_site, load_config
from vector_db.indexer import upsert_product

logger = get_logger(__name__)

async def run_site(site_domain: str, category: str = None, gender: str = None) -> None:
    """Entry point for scraping a single site. Called by scheduler or admin endpoint."""
    global SCRAPED_HASHES
    SCRAPED_HASHES = set()  # Force reset to allow re-triggering for debugging
    logger.info("Starting scrape for %s", site_domain)
    job_id = _start_job(site_domain)

    try:
        # Fetch listing URL from DB
        with get_connection() as conn:
            row = conn.execute("SELECT root_url FROM sites WHERE domain = ?", (site_domain,)).fetchone()
        
        if not row:
            logger.error(f"Domain {site_domain} not found in sites table.")
            return 0
            
        listing_url = row["root_url"]
        
        # Check for cached config first to avoid expensive and flaky AI re-analysis
        config = load_config(site_domain)
        if config:
            logger.info("Using cached scraping config for %s", site_domain)
        else:
            logger.info("No cached config found for %s. Starting discovery...", site_domain)
            listing_html, detail_html, card_html, confirmed_url = await _fetch_html_samples(listing_url)
            
            if not card_html:
                raise ValueError(f"Could not find any product cards for {site_domain}.")

            config = analyze_site(site_domain, listing_html, detail_html, card_html, confirmed_listing_url=confirmed_url)
        
        # Inject category/gender hints if provided
        count = await _scrape_with_config(config, site_domain, listing_url, category=category, gender=gender)
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
        await page.goto(listing_url, wait_until="load", timeout=60_000)
        
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
                    await page.goto(target_cat_url, wait_until="load", timeout=60000)
                except Exception:
                    logger.warning(f"Discovery: Category navigation failed to {target_cat_url}, staying on current page.")
            else:
                logger.info("Discovery: Already on a valid shop/category page.")

        # Wait for actual products to hydrate in the DOM before capturing HTML
        # This is critical for Next.js sites where the product grid is client-side rendered
        try:
            await page.wait_for_function(
                """() => {
                    const headings = document.querySelectorAll(
                        'h1, h2, h3, [class*="title"], [class*="name"]'
                    );
                    for (const el of headings) {
                        if (el.textContent.trim().length > 3) return true;
                    }
                    return false;
                }""",
                timeout=15000
            )
            logger.info("Product text content confirmed in DOM — page fully hydrated.")
        except Exception:
            logger.warning("Timeout waiting for text hydration during discovery. Trying anyway.")

        listing_html = _minimize_html(_strip_head(await page.content()))
        logger.info(f"Listing HTML fetched ({len(listing_html)} chars)")
        logger.info(f"--- LISTING HTML SAMPLE (first 2000 chars) ---\n{listing_html[:2000]}\n--- END LISTING HTML ---")

        # Extract card HTML BEFORE navigating away — we are still on the shop/listing page
        card_html = ""
        try:
            # Try direct card containers first, then fall back to traversing from a product link
            for card_selector in ["div.group", "article.product", "li.product", "[class*='product-card']", "[class*='card']"]:
                cards = await page.query_selector_all(card_selector)
                if len(cards) >= 3:  # Need at least 3 to confirm it's a repeating grid, not a one-off
                    # Use outer_html so AI sees the full wrapper element (e.g. <div class="group">)
                    card_html = await cards[0].evaluate("el => el.outerHTML")
                    logger.info(f"Card sample extracted ({len(card_html)} chars) using {repr(card_selector)}")
                    logger.info(f"--- FULL CARD HTML SAMPLE (Sent to AI) ---\n{card_html}\n--- END CARD HTML ---")
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
                await page.goto(target_url, wait_until="load", timeout=60000)
                detail_html = _minimize_html(_strip_head(await page.content()))
                logger.info(f"Detail HTML fetched ({len(detail_html)} chars)")
                logger.info(f"--- DETAIL HTML SAMPLE (first 2000 chars) ---\n{detail_html[:2000]}\n--- END DETAIL HTML ---")
            except Exception as e:
                logger.warning(f"Failed to navigate to detail page {target_url}: {e}. Proceeding with listing only.")
        else:
            logger.warning("Could not find a valid product link on the listing page.")

        await browser.close()
        logger.info("Samples fetched and browser closed.")
    return listing_html, detail_html, card_html, confirmed_url


async def _scrape_with_config(
    config: dict, 
    site_domain: str, 
    listing_url: str, 
    category: str = None, 
    gender: str = None
) -> int:
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
        
        # Derive expected domain for validation from the actual start URL
        from urllib.parse import urlparse
        expected_domain = urlparse(start_url).netloc.replace("www.", "")
        logger.info(f"Validation will expect domain: {expected_domain}")
        logger.info(f"Using selectors: {json.dumps(config.get('fields', {}), indent=2)}")

        await page.goto(start_url, wait_until="load", timeout=60_000)
        logger.info(f"Page loaded: {page.url} | Title: {await page.title()}")

        page_num = 1
        while True:
            logger.info(f"Processing listing page {page_num}…")
            
            # Wait for products to hydrate (Next.js renders client-side after networkidle)
            try:
                await page.wait_for_function(
                    """() => {
                        const headings = document.querySelectorAll(
                            'h1, h2, h3, [class*="title"], [class*="name"]'
                        );
                        for (const el of headings) {
                            if (el.textContent.trim().length > 3) return true;
                        }
                        return false;
                    }""",
                    timeout=15000
                )
                logger.info("Product text content confirmed in DOM — page fully hydrated.")
            except Exception:
                logger.warning(f"Timeout waiting for text hydration on page {page_num}. Trying anyway.")

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
            logger.info(f"Page {page_num}: Found {len(cards)} cards using selector '{card_selector}'")
            
            page_processed_count = 0
            for i, card in enumerate(cards):
                product = await _extract_product(card, config, site_domain, page.url)
                if product:
                    logger.info(f"Card {i} Extracted: {json.dumps(product, indent=2)}")
                    if not _already_scraped(product):
                        try:
                            # Inject manual category/gender hints if they were passed at trigger time
                            if category: product["category"] = category
                            if gender: product["gender"] = gender

                            validated = await validate_product(product, expected_domain)
                            await upsert_product(validated)
                            _register_hash(validated)
                            count += 1
                            page_processed_count += 1
                        except ValidationError as ve:
                            card_html = await card.evaluate("el => el.outerHTML")
                            logger.warning(f"Product {i} failed validation: {ve}")
                            logger.info(f"--- FAILING CARD HTML ---\n{card_html}\n--- END CARD HTML ---")
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
                await page.wait_for_load_state("load", timeout=15000)
                page_num += 1
            except Exception as e:
                logger.warning(f"Pagination failed: {e}. Stopping.")
                break

        await browser.close()
        logger.info(f"Scrape process complete. Total products added: {count}")
    return count


async def _extract_product(card, config: dict, site_domain: str, base_url: str) -> dict | None:
    """Extract raw product fields efficiently by getting HTML once and using BeautifulSoup."""
    fields = config.get("fields", {})
    try:
        # Get full card HTML to avoid multiple browser roundtrips
        card_html = await card.evaluate("el => el.outerHTML")
        soup = BeautifulSoup(card_html, "lxml")
        
        def get_text(selector):
            if not selector: return ""
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else ""

        def get_attr(selector, attr):
            if not selector: return ""
            el = soup.select_one(selector)
            return el.get(attr, "") if el else ""

        name      = get_text(fields.get("name", ""))
        price_raw = get_text(fields.get("price", ""))
        
        # Images often have data-src or similar
        img_selector = fields.get("image_url", "")
        image = ""
        if img_selector:
            img_el = soup.select_one(img_selector)
            if img_el:
                image = img_el.get("src") or img_el.get("data-src") or img_el.get("srcset", "").split(" ")[0] or ""

        url_raw = get_attr(fields.get("product_url", ""), "href")

        if not name: return None

        # Resolve relative URLs
        image   = urljoin(base_url, image)   if image   else ""
        url_raw = urljoin(base_url, url_raw) if url_raw else ""

        # Clean price
        import re
        price_no_nbsp = price_raw.replace("\xa0", " ").replace(",", "").strip()
        price_match   = re.search(r"(\d+[\d.]*)", price_no_nbsp)
        price_cleaned = price_match.group(1) if price_match else ""

        return {
            "product_name": name,
            "price":        price_cleaned,
            "image_url":    image,
            "product_url":  url_raw,
            "source_site":  site_domain,
            "scraped_at":   datetime.now(timezone.utc).isoformat(),
            "is_active":    True,
        }
    except Exception as e:
        logger.debug("Extraction error on card: %s", e)
        return None


def _strip_head(html: str) -> str:
    """Remove the <head> element from HTML to reduce noise for logging and LLM analysis."""
    if not html:
        return ""
    return re.sub(r"<head>.*?</head>", "", html, flags=re.DOTALL | re.IGNORECASE)


def _minimize_html(html: str) -> str:
    """
    Minimize HTML by removing redundant sibling elements with identical semantic structures.
    This version is aggressive against unique IDs and metadata blobs (like Shopify JSON)
    to ensure the AI receives a compact, template-like view of the page.
    """
    if not html:
        return ""
    
    # Use lxml for speed
    soup = BeautifulSoup(html, "lxml")
    
    # 1. Global Stripping of high-noise/high-bulk elements
    # We remove scripts/styles entirely. For SVGs, we clear paths but keep the tag 
    # to let the AI know an icon is present (useful for selectors).
    for tag in soup.find_all(["script", "style", "svg", "noscript"]):
        if tag.name == "svg":
            tag.clear() 
        else:
            tag.decompose()

    # Blacklist of attributes that are either too large or unique per-item (non-semantic).
    # Stripping these allows the deduplication logic to see through 'watermarked' elements.
    ATTR_BLACKLIST = {
        "id", "href", "src", "srcset", "style", "title", "alt", 
        "data-product-id", "data-variant-id", "data-id", "data-view-id"
    }

    def prune(element):
        # Group children by their semantic signature (tag and class)
        children = element.find_all(recursive=False)
        seen_signatures = set()
        
        for child in children:
            # First, strip non-semantic attributes from this child
            for attr in list(child.attrs.keys()):
                if attr in ATTR_BLACKLIST or attr.startswith("data-json-") or attr.startswith("data-view-"):
                    del child[attr]
            
            # Recursive call to prune deep structures first
            prune(child)
            
            # Signature is tag name and its classes (the most semantic attribute)
            # We ignore other attributes like 'id' or 'href' for repeating detection
            classes = child.get("class", [])
            if isinstance(classes, list):
                classes = tuple(sorted(classes))
            elif isinstance(classes, str):
                classes = (classes,)
            else:
                classes = ()
            
            signature = (child.name, classes)
            
            # If we've seen this exact tag+class combo as a sibling, it's a repeat
            if signature in seen_signatures:
                child.decompose()
            else:
                seen_signatures.add(signature)
                
    # Prune from body if it exists, otherwise from soup root
    target = soup.body if soup.body else soup
    prune(target)
    
    # Return as string, removing extra whitespace but keeping it somewhat readable
    content = str(soup)
    # Collapse multiple spaces/newlines into single spaces
    content = re.sub(r"\s+", " ", content).strip()
    return content


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
