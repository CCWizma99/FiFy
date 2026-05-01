"""
scraper/pipeline/validator.py
Data validation layer — every product passes through here before
reaching the embedding engine.

Rules:
  - image_url must return HTTP 200
  - product_name must not be empty
  - price must be parseable as float
  - product_url must resolve to the expected domain
"""
import httpx
from urllib.parse import urlparse

from backend.utils.logger import get_logger
from scraper.pipeline.dead_letter import log_dead_letter

logger = get_logger(__name__)


class ValidationError(Exception):
    pass


async def validate_product(product: dict, expected_domain: str, check_image: bool = True) -> dict:
    """
    Validate a scraped product dict. Raises ValidationError if invalid.
    Returns the cleaned product dict on success.
    """
    errors = []

    # 1. Product name
    if not product.get("product_name", "").strip():
        errors.append("product_name is empty")

    # 2. Price
    try:
        product["price"] = float(str(product.get("price", "")).replace("$", "").replace(",", "").strip())
    except (ValueError, TypeError):
        errors.append(f"price not parseable: {product.get('price')!r}")

    # 3. Product URL domain
    product_url = product.get("product_url", "")
    parsed = urlparse(product_url)
    if expected_domain not in parsed.netloc:
        errors.append(f"product_url domain mismatch: {parsed.netloc!r}")

    # 4. Image URL reachability (Optional)
    image_url = product.get("image_url", "")
    if image_url:
        if check_image:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.head(image_url, follow_redirects=True)
                if resp.status_code != 200:
                    errors.append(f"image_url returned {resp.status_code}")
            except Exception as e:
                errors.append(f"image_url unreachable: {e}")
    else:
        errors.append("image_url is missing")

    if errors:
        reason = "; ".join(errors)
        log_dead_letter(product, reason)
        raise ValidationError(f"Product failed validation: {reason}")

    return product
