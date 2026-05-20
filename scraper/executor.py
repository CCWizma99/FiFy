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
            
            # VERIFY CONFIG: Stop if AI produced garbage or incomplete fields
            fields = config.get("fields", {})
            if not config or not all(fields.get(f) for f in ["name", "price", "image_url"]):
                raise ValueError(f"Site analysis for {site_domain} produced an incomplete config (missing name, price, or image).")
        
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
        # Look for "Shop", "Men", "Women", "Clothing", "Collections", etc.
        category_link = await page.query_selector(
            "a[href*='shop'], a[href*='category'], a[href*='men'], a[href*='women'], "
            "a[href*='clothing'], a[href*='collection'], a[href*='new-in'], a[href*='all']"
        )
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
                    // Wait until we see at least 3 elements that look like product cards
                    const cardSelectors = [
                        '.nt_grid_item', '.product-card', '.product-item', 
                        '[data-product-id]', '.grid__item', '.card'
                    ];
                    for (const sel of cardSelectors) {
                        if (document.querySelectorAll(sel).length >= 3) return true;
                    }
                    // Fallback: wait for at least 3 links that look like products
                    const productLinks = Array.from(document.querySelectorAll('a[href*="product"]'))
                        .filter(a => a.href.includes('/products/'));
                    return productLinks.length >= 3;
                }""",
                timeout=30000
            )
            logger.info("Product grid confirmed in DOM — page fully hydrated.")
        except Exception:
            logger.warning("Timeout waiting for product grid hydration. Capturing current state.")

        listing_raw = await page.content()
        if len(listing_raw) < 7000:
            logger.warning(f"Extracted HTML is suspiciously small ({len(listing_raw)} chars). Page may be blocked or unhydrated.")

        listing_html = _minimize_html(_strip_head(listing_raw))
        logger.info(f"Listing HTML fetched ({len(listing_html)} chars)")
        logger.info(f"--- FULL LISTING HTML SENT TO AI ---\n{listing_html}\n--- END LISTING HTML ---")

        # Extract card HTML BEFORE navigating away — we are still on the shop/listing page
        card_html = ""
        try:
            # Try direct card containers first, then fall back to traversing from a product link
            # [data-product-id] is the gold standard for Shopify/E-commerce sites.
            for card_selector in [
                ".nt_grid_item", ".product-card", ".product-item", "[data-product-id]",
                ".grid-product", ".product-grid-item", ".card-product", ".product-inner",
                "div.group", "article.product", "li.product", "[class*='product-card']",
                ".grid-item", ".product", ".item"
            ]:
                cards = await page.query_selector_all(card_selector)
                if len(cards) >= 2:  # Reduced to 2 to be more aggressive
                    # Use outer_html so AI sees the full wrapper element
                    card_html = await cards[0].evaluate("el => el.outerHTML")
                    logger.info(f"Card sample extracted ({len(card_html)} chars) using {repr(card_selector)}")
                    break
            
            # Fallback: traverse from product link to its closest semantic container
            if not card_html:
                links = await page.query_selector_all("a[href*='product']")
                if links:
                    # Look for the container that contains this link AND likely has a price/name nearby
                    parent_html = await links[0].evaluate(
                        r"""el => {
                            let current = el;
                            for (let i = 0; i < 5; i++) { // Go up max 5 levels
                                if (!current || current.tagName === 'BODY') break;
                                const text = current.innerText || "";
                                // If this container has price-like numbers, it's likely our full card
                                if (/\d+[\d,.]*/.test(text) && text.length > 20) return current.outerHTML;
                                current = current.parentElement;
                            }
                            return (el.closest('li') || el.closest('article') || el.closest('div[class]') || el.parentElement)?.outerHTML || '';
                        }"""
                    )
                    if parent_html:
                        card_html = parent_html[:5000] # Increased limit to ensure we get full card context
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
                logger.info(f"--- FULL DETAIL HTML SENT TO AI ---\n{detail_html}\n--- END DETAIL HTML ---")
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
                        except Exception as e:
                            # CRITICAL: Stop on connection errors
                            err_msg = str(e).lower()
                            if "connect" in err_msg or "getaddrinfo" in err_msg or "timeout" in err_msg:
                                logger.error(f"CRITICAL ERROR: Connection lost during indexing ({e}). Aborting scrape.")
                                if browser: await browser.close()
                                return count

                            card_html = await card.evaluate("el => el.outerHTML")
                            logger.warning(f"Product {i} failed validation/indexing: {e}")
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
    """
    Extract raw product fields by trying multiple layout variants in the site profile.
    Returns the first successful extraction.
    """
    # If this is a new-style profile with multiple variants, try them all
    variants = config.get("variants", [])
    if not variants:
        # Fallback for old-style single config dict
        variants = [{"fields": config.get("fields", {}), "id": "primary"}]

    for variant in variants:
        fields = variant.get("fields", {})
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
            
            # If we didn't get at least a name, this variant probably doesn't match this page
            if not name:
                continue

            # Images often have various lazy-load attributes or are inside <picture> tags.
            # We check a priority list of attributes commonly used across e-commerce platforms.
            img_selector = fields.get("image_url", "")
            image = ""
            if img_selector:
                img_el = soup.select_one(img_selector)
                if img_el:
                    # Priority 1: Check common lazy-load attributes
                    # data-original and data-lazy-src are common in custom themes
                    for attr in ["data-original", "data-bgset", "data-src", "data-lazy-src", "data-srcset", "src", "srcset", "style", "data-lazy"]:
                        val = img_el.get(attr)
                        if val:
                            if attr == "style" and "background-image" in val:
                                match = re.search(r'url\((["\']?)(.*?)\1\)', val)
                                if match:
                                    image = match.group(2)
                                    break
                            else:
                                image = val.split(" ")[0] if attr in ["srcset", "data-srcset", "data-bgset"] else val
                                break
                    
                    # Priority 2: If it's a wrapper, look for a standard img tag inside
                    if not image and img_el.name != "img":
                        sub_img = img_el.find("img")
                        if sub_img:
                            for attr in ["data-src", "src", "srcset"]:
                                val = sub_img.get(attr)
                                if val:
                                    image = val.split(" ")[0] if attr == "srcset" else val
                                    break
                    
                    # Priority 3: Check for <source> tags (common in modern responsive designs)
                    if not image:
                        source = img_el.find("source") or (img_el.parent.find("source") if img_el.parent else None)
                        if source:
                            image = source.get("data-srcset", "").split(" ")[0] or source.get("srcset", "").split(" ")[0] or ""

            # Normalize and clean the URL (handles protocol-relative and thumbnail suffixes)
            image = _clean_image_url(image, base_url)

            # Logo-Buster: skip images that look like site UI elements
            junk_keywords = ["logo", "icon", "banner", "pixel", "loading", "spinner", "placeholder", "badge", "mintpay", "appstore", "playstore"]
            if image and any(k in image.lower() for k in junk_keywords):
                logger.debug(f"Skipping junk image detected during extraction: {image}")
                image = ""

            # Better product URL detection: ignore vendor/search links
            links = soup.find_all("a", href=True)
            url_raw = ""
            for a in links:
                href = a.get("href", "")
                # Skip vendor filters, search links, and query-only links
                if any(x in href.lower() for x in ["/vendors", "?q=", "/search", "/collections/all"]):
                    continue
                url_raw = href
                break
            
            # Fallback to selector if logic above found nothing
            if not url_raw:
                url_raw = get_attr(fields.get("product_url", ""), "href")

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
            logger.debug(f"Variant '{variant.get('id')}' failed for card: {e}")
            continue

    return None


def _clean_image_url(url: str, base_url: str) -> str:
    """Normalize and clean image URLs to handle lazy-load relics and ensure high quality."""
    if not url: return ""
    
    # Handle protocol-relative URLs (//example.com -> https://example.com)
    if url.startswith("//"):
        url = "https:" + url
        
    # Resolve relative paths
    url = urljoin(base_url, url)
    
    # Heuristic: Strip common thumbnail size suffixes (e.g. -150x150, _300x)
    # to retrieve the original high-resolution image.
    url = re.sub(r"[-_]\d+x\d*\.(jpg|png|jpeg|webp)", r".\1", url, flags=re.IGNORECASE)
    
    return url


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

    ATTR_BLACKLIST = {
        "style", "title", "alt", "aria-hidden", "tabindex", "role"
    }

    def prune(element):
        # Group children by their semantic signature (tag and class)
        children = element.find_all(recursive=False)
        seen_signatures = set()
        
        for child in children:
            # Recursive call to prune deep structures first
            prune(child)
            
            # Signature is tag name and its classes
            # We ignore IDs and other unique attributes for repeating detection
            # so that multiple cards are seen as the "same" template.
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
                # Keep the element, but strip noisy attributes for the signature generation 
                # (Note: attributes preserved in output per instruction)
                seen_signatures.add(signature)
                
    # Prune from body if it exists, otherwise from soup root
    target = soup.body if soup.body else soup
    prune(target)
    
    # Return as string, removing extra whitespace but keeping it somewhat readable
    content = str(soup)
    # Collapse multiple spaces/newlines into single spaces
    content = re.sub(r"\s+", " ", content).strip()
    return content


def _normalize_url(url: str) -> str:
    """Strip query parameters and fragments to prevent duplicate indexing of the same page."""
    if not url: return ""
    return url.split("?")[0].split("#")[0].rstrip("/")


def _generate_content_hash(product: dict) -> str:
    """
    Generate a fingerprint based on the semantic content of the product.
    This prevents duplicates where the same product has different URLs.
    """
    # Name + Price + Image URL is a very strong signature for uniqueness
    name = str(product.get("product_name", "")).strip().lower()
    price = str(product.get("price", "")).strip()
    image = str(product.get("image_url", "")).strip()
    fingerprint = f"{name}|{price}|{image}"
    return hashlib.md5(fingerprint.encode()).hexdigest()


def _already_scraped(product: dict) -> bool:
    """
    Check if a product has already been indexed using a two-tier check:
    1. Normalized URL check (fast)
    2. Content fingerprint check (robust)
    """
    url = _normalize_url(product["product_url"])
    content_hash = _generate_content_hash(product)
    site_domain = product.get("source_site", "")

    with get_connection() as conn:
        # Check 1: Exact Normalized URL
        row = conn.execute(
            "SELECT 1 FROM url_hashes WHERE url = ?", (url,)
        ).fetchone()
        if row: return True

        # Check 2: Content Hash (within the same site)
        if content_hash and site_domain:
            row = conn.execute(
                "SELECT 1 FROM url_hashes WHERE site_domain = ? AND content_hash = ?",
                (site_domain, content_hash)
            ).fetchone()
            if row: return True

    return False


def _register_hash(product: dict) -> None:
    """Store both the normalized URL and the content fingerprint in the deduplication registry."""
    url = _normalize_url(product["product_url"])
    url_hash = hashlib.md5(url.encode()).hexdigest()
    content_hash = _generate_content_hash(product)
    site_domain = product.get("source_site", "")
    
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO url_hashes 
            (url, site_domain, hash, content_hash, last_seen) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                url, 
                site_domain, 
                url_hash, 
                content_hash, 
                datetime.now(timezone.utc).isoformat()
            ),
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
