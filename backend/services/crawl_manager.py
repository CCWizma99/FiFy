import asyncio
import json
from typing import Dict, List, Set
from scraper.spider import Spider
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class CrawlManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CrawlManager, cls).__new__(cls)
            cls._instance.active_spiders: Dict[int, Spider] = {}
            cls._instance.log_queues: Dict[int, Set[asyncio.Queue]] = {}
        return cls._instance

    async def start_crawl(self, site_id: int):
        if site_id in self.active_spiders:
            logger.warning(f"Spider for site {site_id} already active.")
            return

        spider = Spider(site_id, on_log=lambda data: self._broadcast_log(site_id, data))
        self.active_spiders[site_id] = spider
        
        asyncio.create_task(self._run_spider(site_id, spider))

    async def _run_spider(self, site_id: int, spider: Spider):
        try:
            await spider.run()
        finally:
            del self.active_spiders[site_id]
            self._broadcast_log(site_id, {"type": "status", "message": "finished"})

    def pause_crawl(self, site_id: int):
        if site_id in self.active_spiders:
            self.active_spiders[site_id].is_paused = True
            self._broadcast_log(site_id, {"type": "status", "message": "paused"})

    def resume_crawl(self, site_id: int):
        if site_id in self.active_spiders:
            self.active_spiders[site_id].is_paused = False
            self._broadcast_log(site_id, {"type": "status", "message": "resumed"})

    def stop_crawl(self, site_id: int):
        if site_id in self.active_spiders:
            self.active_spiders[site_id].is_stopped = True
            self._broadcast_log(site_id, {"type": "status", "message": "stopped"})

    def _broadcast_log(self, site_id: int, data: dict):
        if site_id in self.log_queues:
            for queue in self.log_queues[site_id]:
                queue.put_nowait(json.dumps(data))

    async def subscribe_logs(self, site_id: int) -> asyncio.Queue:
        queue = asyncio.Queue()
        if site_id not in self.log_queues:
            self.log_queues[site_id] = set()
        self.log_queues[site_id].add(queue)
        return queue

    def unsubscribe_logs(self, site_id: int, queue: asyncio.Queue):
        if site_id in self.log_queues:
            self.log_queues[site_id].discard(queue)

crawl_manager = CrawlManager()
