"""
backend/routers/products.py
GET /products/{id} — fetch single product metadata from Qdrant by ID.
"""
from fastapi import APIRouter, HTTPException

from backend.services.qdrant_service import get_product_by_id

router = APIRouter()


@router.get("/{product_id}")
async def get_product(product_id: str):
    """Return full metadata for a single product by its Qdrant point ID."""
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found.")
    return product
