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
        self._log(f"Starting spider for {self.domain}...")
        
        # Ensure root URL is in queue
        self._enqueue(self.root_url, depth=0)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
            page = await context.new_page()

            # Ensure we have a config
            if not self.config:
                logger.info(f"No config found for {self.domain}, running Site Analyzer...")
                self.config = await analyze_site(self.root_url)
                if not self.config:
                    logger.error(f"Failed to analyze site {self.domain}. Aborting.")
                    return

            while not self.is_stopped:
                if self.is_paused:
                    await asyncio.sleep(1)
                    continue

                url_data = self._get_next_url()
                if not url_data:
                    logger.info(f"No more URLs to crawl for {self.domain}.")
                    break

                url = url_data["url"]
                self.current_url = url
                depth = url_data["depth"]
                self._log(f"Crawling: {url} (Depth: {depth})")

                try:
                    await self._process_page(page, url, depth)
                    self._mark_done(url)
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")
                    self._mark_failed(url, str(e))

                # Rate limiting
                await asyncio.sleep(2)

            await browser.close()
            logger.info(f"Spider for {self.domain} finished.")

    async def _process_page(self, page, url, depth):
        """Processes a single page: extract links and products."""
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # 1. Discover Links (if within depth limit)
        if depth < 3: # Max depth 3 for now
            links = await page.query_selector_all("a[href]")
            for link_el in links:
                href = await link_el.get_attribute("href")
                if href:
                    absolute_url = urljoin(url, href)
                    if self._is_internal(absolute_url):
                        self._enqueue(absolute_url, depth + 1)

        # 2. Extract Products (if it looks like a listing or product page)
        product_card_selector = self.config.get("product_card_selector")
        if product_card_selector:
            cards = await page.query_selector_all(product_card_selector)
            if cards:
                self._log(f"Found {len(cards)} product cards on {url}")
                for card in cards:
                    product = await _extract_product(card, self.config, self.domain, url)
                    if product and not _already_scraped(product):
                        if validate_product(product):
                            try:
                                await upsert_product(product)
                                _register_hash(product)
                                self._log(f"Indexed product: {product['product_name']}")
                                self._increment_product_count()
                            except Exception as e:
                                logger.error(f"Failed to index {product['product_name']}: {e}")
                        else:
                            logger.warning(f"Product validation failed: {product['product_name']}")

    def _is_internal(self, url: str) -> bool:
        """Check if URL belongs to the same domain and isn't a junk file."""
        parsed = urlparse(url)
        # Check domain
        if parsed.netloc and parsed.netloc != self.domain and not parsed.netloc.endswith("." + self.domain):
            return False
        
        # Check file extension
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in [".jpg", ".png", ".pdf", ".zip", ".mp4"]):
            return False
            
        return True

    def _enqueue(self, url: str, depth: int):
        """Adds a URL to the crawl queue if not already there."""
        # Strip fragments
        url = url.split("#")[0].rstrip("/")
        
        with get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO crawl_queue (site_id, url, depth, status)
                VALUES (?, ?, ?, 'pending')
            """, (self.site_id, url, depth))
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
