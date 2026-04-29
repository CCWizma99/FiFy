"""
backend/models/search.py
Pydantic request/response schemas for search endpoints.
"""
from pydantic import BaseModel, HttpUrl
from typing import Optional


class ProductResult(BaseModel):
    id: str
    product_name: str
    brand: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "USD"
    category: Optional[str] = None
    gender: Optional[str] = None
    product_url: str
    image_url: str
    source_site: str
    score: float  # cosine similarity score from Qdrant


class SearchResponse(BaseModel):
    query_type: str  # "image" or "text"
    results: list[ProductResult]
    total: int
