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
