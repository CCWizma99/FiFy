"""
backend/utils/validators.py
Input validation helpers for search endpoints.
"""
from fastapi import UploadFile, HTTPException

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_TEXT_LENGTH = 200


async def validate_image(file: UploadFile) -> bytes:
    """Validate uploaded image: type and size. Returns raw bytes."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type '{file.content_type}'. Use JPEG, PNG, or WebP.",
        )
    contents = await file.read()
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large ({len(contents) / 1024 / 1024:.1f} MB). Max 5 MB.",
        )
    return contents


def validate_text_query(query: str) -> str:
    """Validate text search query: not empty, not too long."""
    query = query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Search query must not be empty.")
    if len(query) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Query too long ({len(query)} chars). Max {MAX_TEXT_LENGTH}.",
        )
    return query
