"""
tests/test_validation.py
Tests for the product data validation pipeline.
"""
import pytest

from scraper.pipeline.validator import validate_product, ValidationError


VALID_PRODUCT = {
    "product_name": "Floral Midi Dress",
    "price": "45.99",
    "product_url": "https://asos.com/products/floral-midi-dress",
    "image_url": "https://images.asos-media.com/products/floral.jpg",
    "source_site": "asos.com",
}


@pytest.mark.asyncio
async def test_empty_product_name_fails():
    product = {**VALID_PRODUCT, "product_name": ""}
    with pytest.raises(ValidationError, match="product_name"):
        await validate_product(product, "asos.com")


@pytest.mark.asyncio
async def test_invalid_price_fails():
    product = {**VALID_PRODUCT, "price": "not-a-price"}
    with pytest.raises(ValidationError, match="price"):
        await validate_product(product, "asos.com")


@pytest.mark.asyncio
async def test_wrong_domain_fails():
    product = {**VALID_PRODUCT, "product_url": "https://competitor.com/item"}
    with pytest.raises(ValidationError, match="domain"):
        await validate_product(product, "asos.com")


@pytest.mark.asyncio
async def test_price_cleaned_correctly():
    """Dollar sign and commas should be stripped from price strings."""
    product = {**VALID_PRODUCT, "price": "$1,299.99"}
    # This will also attempt the image URL check — mock it
    from unittest.mock import patch, AsyncMock
    import httpx

    mock_response = AsyncMock()
    mock_response.status_code = 200
    with patch("httpx.AsyncClient.head", return_value=mock_response):
        result = await validate_product(product, "asos.com")
    assert result["price"] == 1299.99
