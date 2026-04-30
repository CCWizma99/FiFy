"""
backend/models/job.py
Pydantic schemas for scrape job status responses.
"""
from pydantic import BaseModel
from typing import Optional


class ScrapeJobStatus(BaseModel):
    id: int
    site: str
    started_at: str
    finished_at: Optional[str] = None
    status: str  # "running" | "completed" | "failed"
    products_scraped: int = 0
    error_message: Optional[str] = None


class ScrapeJobsResponse(BaseModel):
    jobs: list[ScrapeJobStatus]


class ScraperStats(BaseModel):
    total_products: int
    active_products: int
    total_jobs: int
    success_rate: float
    failed_products_count: int


class DeadLetterEntry(BaseModel):
    timestamp: str
    reason: str
    product_url: Optional[str] = None
    source_site: Optional[str] = None
    retried: bool = False


class TargetSite(BaseModel):
    domain: str
    root_url: str
    is_active: bool = True
