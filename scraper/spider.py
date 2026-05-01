import asyncio
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright
from backend.database import get_connection
from backend.utils.logger import get_logger
from scraper.executor import _minimize_html, _strip_head, _extract_product, _register_hash, _already_scraped
from scraper.site_analyzer.agent import analyze_site, load_config
from scraper.pipeline.validator import validate_product
from vector_db.indexer import upsert_product

logger = get_logger(__name__)

class Spider:
    def __init__(self, site_id: int, on_log=None):
        self.site_id = site_id
        self.on_log = on_log
        self.domain = ""
        self.root_url = ""
        self.config = {}
        self.is_paused = False
        self.is_stopped = False
        self._load_site_info()

    def _load_site_info(self):
        with get_connection() as conn:
            row = conn.execute("SELECT domain, root_url FROM sites WHERE id = ?", (self.site_id,)).fetchone()
            if row:
                self.domain = row["domain"]
                self.root_url = row["root_url"]
                self.config = load_config(self.domain) or {}

    def _log(self, message: str, level: str = "info"):
        logger.info(message)
        if self.on_log:
            self.on_log({"type": level, "message": message, "url": self.current_url if hasattr(self, "current_url") else ""})

    async def run(self):
        """Main crawl loop."""
        self._log(f"Initializing spider for {self.domain}...")
        
        # Ensure root URL is in queue
        self._enqueue(self.root_url, depth=0)
        
        async with async_playwright() as p:
            self._log("Launching browser engine...")
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                # 1. Ensure we have a config (analyze site if needed)
                if not self.config:
                    self._log("No configuration found. Analyzing site structure...")
                    try:
                        from scraper.executor import _fetch_html_samples
                        listing_html, detail_html, card_html, confirmed_url = await _fetch_html_samples(self.root_url)
                        
                        if not card_html:
                            self._log("Discovery failed: Could not find product cards.", level="error")
                            return

                        self.config = analyze_site(self.domain, listing_html, detail_html, card_html, confirmed_listing_url=confirmed_url)
                        self._log("Site structure successfully analyzed.")
                    except Exception as e:
                        self._log(f"Site analysis failed: {str(e)}", level="error")
                        return

                # 2. Start Processing Queue
                while not self.is_stopped:
                    if self.is_paused:
                        await asyncio.sleep(1)
                        continue

                    url_data = self._get_next_url()
                    if not url_data:
                        self._log(f"All discovered URLs processed for {self.domain}.")
                        break

                    url = url_data["url"]
                    self.current_url = url
                    depth = url_data["depth"]
                    
                    try:
                        import time
                        start_time = time.time()
                        self._log(f"Visiting: {url} (Depth: {depth})")
                        await self._process_page(page, url, depth)
                        self._mark_done(url)
                        elapsed = time.time() - start_time
                        logger.info(f"Page processed in {elapsed:.2f}s: {url}")
                    except Exception as e:
                        if "net::ERR_INTERNET_DISCONNECTED" in str(e):
                            self._log("Internet disconnected. Spider pausing for 30s...", level="warning")
                            await asyncio.sleep(30)
                            # Put it back to pending
                            self._mark_pending(url)
                            continue

                        self._log(f"Failed to process {url}: {str(e)}", level="error")
                        self._mark_failed(url, str(e))

                    await asyncio.sleep(2)
            finally:
                await browser.close()
                self._log(f"Spider execution finished for {self.domain}.")

    async def _process_page(self, page, url, depth):
        """Processes a single page: extract links and products."""
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # 1. Discover Links (if within depth limit)
        if depth < 3: # Max depth 3 for now
            links = await page.query_selector_all("a[href]")
            found_count = 0
            enqueued_count = 0
            for link_el in links:
                href = await link_el.get_attribute("href")
                if href:
                    absolute_url = urljoin(url, href)
                    if self._is_internal(absolute_url) and self._is_relevant(absolute_url):
                        found_count += 1
                        if self._enqueue(absolute_url, depth + 1):
                            enqueued_count += 1
            if enqueued_count > 0:
                logger.info(f"Discovered {found_count} relevant links on {url} ({enqueued_count} new enqueued)")

        # 2. Extract Products (if it looks like a listing or product page)
        product_card_selector = self.config.get("product_card_selector")
        if product_card_selector:
            cards = await page.query_selector_all(product_card_selector)
            if cards:
                self._log(f"Found {len(cards)} product cards on {url}")
                for card in cards:
                    product = await _extract_product(card, self.config, self.domain, url)
                    if product and not _already_scraped(product):
                        try:
                            # validate_product is async and requires the expected domain
                            # We skip image check during crawl for speed
                            validated = await validate_product(product, self.domain, check_image=False)
                            await upsert_product(validated)
                            _register_hash(validated)
                            self._log(f"Indexed product: {validated['product_name']}")
                            self._increment_product_count()
                        except Exception as e:
                            logger.warning(f"Product validation failed: {product.get('product_name')} - {e}")

    def _is_relevant(self, url: str) -> bool:
        """Heuristic to prioritize fashion-related pages and avoid fluff."""
        u = url.lower()
        # Blacklist common high-noise but internal paths
        if any(x in u for x in ["/account", "/cart", "/checkout", "/login", "/register", "/search", "terms", "privacy", "policy", "contact", "about"]):
            return False
        
        # Priority keywords (if depth > 0, we might want to be stricter, but for now let's allow anything not blacklisted)
        # However, to avoid "mobile-phones" on a multi-store:
        if "thilakawardhana.com" in u:
            # If it's this specific site, we know they have non-fashion stuff
            # Only allow if it has fashion keywords OR is a collection/product
            fashion_keywords = ["women", "men", "kids", "clothing", "fashion", "wear", "dress", "top", "bottom", "shoe", "bag", "accessory", "innerwear", "collection"]
            if not any(k in u for k in fashion_keywords):
                return False
                
        return True

    def _is_internal(self, url: str) -> bool:
        """Check if URL belongs to the same domain and isn't a junk file."""
        parsed = urlparse(url)
        # Check domain
        if parsed.netloc and parsed.netloc != self.domain and not parsed.netloc.endswith("." + self.domain):
            return False
        
        # Check file extension
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in [".jpg", ".png", ".pdf", ".zip", ".mp4", ".css", ".js"]):
            return False
            
        return True

    def _enqueue(self, url: str, depth: int) -> bool:
        """Adds a URL to the crawl queue if not already there. Returns True if new."""
        # Strip fragments and trailing slashes for normalization
        url = url.split("#")[0].rstrip("/")
        if not url: return False
        
        with get_connection() as conn:
            cur = conn.execute("""
                INSERT OR IGNORE INTO crawl_queue (site_id, url, depth, status)
                VALUES (?, ?, ?, 'pending')
            """, (self.site_id, url, depth))
            conn.commit()
            return cur.rowcount > 0

    def _mark_pending(self, url: str):
        with get_connection() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'pending' WHERE site_id = ? AND url = ?", (self.site_id, url))
            conn.commit()

    def _get_next_url(self):
        """Gets the next pending URL from the queue."""
        with get_connection() as conn:
            row = conn.execute("""
                SELECT url, depth FROM crawl_queue 
                WHERE site_id = ? AND status = 'pending' 
                ORDER BY depth ASC, id ASC LIMIT 1
            """, (self.site_id,)).fetchone()
            
            if row:
                url = row["url"]
                conn.execute("UPDATE crawl_queue SET status = 'processing' WHERE site_id = ? AND url = ?", (self.site_id, url))
                conn.commit()
                return {"url": url, "depth": row["depth"]}
        return None

    def _increment_product_count(self):
        with get_connection() as conn:
            conn.execute("UPDATE sites SET total_products = total_products + 1 WHERE id = ?", (self.site_id,))
            conn.commit()

    def _mark_done(self, url: str):
        with get_connection() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'done' WHERE site_id = ? AND url = ?", (self.site_id, url))
            conn.commit()

    def _mark_failed(self, url: str, error: str):
        with get_connection() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'failed', error = ? WHERE site_id = ? AND url = ?", (self.site_id, error, url))
            conn.commit()
