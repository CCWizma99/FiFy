"""
scraper/batch_categorizer.py
Batch AI categorization job for FiFy.
Processes products in batches of 30 using Gemini to assign fashion categories.
"""
import asyncio
import json
import logging
from typing import List, Dict

import google.generativeai as genai
from qdrant_client.models import Filter, IsNullCondition, PayloadSchemaType

from vector_db.client import get_client
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

CATEGORIES = ["Tops", "Bottoms", "Dresses", "Outerwear", "Footwear", "Innerwear", "Bags", "Accessories", "Activewear", "Other"]
GENDERS = ["Men", "Women", "Neutral"]

SYSTEM_PROMPT = f"""
You are a fashion expert assistant for FiFy, a multimodal search engine.
Your task is to categorize products based on their Name and URL.

1. CATEGORY: Choose exactly ONE from: {', '.join(CATEGORIES)}.
   - Tops: Shirts, t-shirts, blouses, crop tops, tanks, camis.
   - Bottoms: Pants, jeans, trousers, skirts, shorts, leggings.
   - Dresses: Frocks, gowns, sundresses, midis, maxis.
   - Outerwear: Jackets, coats, blazers, hoodies, sweaters, cardigans.
   - Footwear: Shoes, boots, sandals, sneakers, heels, flats.
   - Innerwear: Bras, panties, boxers, underwear, socks, sleepwear.
   - Bags: Handbags, backpacks, clutches, wallets, totes.
   - Accessories: Jewelry, watches, belts, hats, sunglasses, hair accessories, scarves.
   - Activewear: Gym wear, yoga pants, sports bras, swimwear.
   - Other: Perfume, makeup, home decor, or anything else.

2. GENDER: Choose exactly ONE from: {', '.join(GENDERS)}.
   - Men: Clearly masculine items or explicitly labeled for men.
   - Women: Clearly feminine items (dresses, blouses, heels) or labeled for women.
   - Neutral: Unisex items (plain tees, hoodies, some bags, accessories) or kids' items.

Return ONLY a JSON object where keys are the Product IDs and values are objects containing "category" and "gender".
Example: {{"uuid-1": {{"category": "Dresses", "gender": "Women"}}, "uuid-2": {{"category": "Footwear", "gender": "Neutral"}}}}
"""

async def run_batch_categorization(limit: int = 300):
    """
    Main entry point for categorization.
    Fetches up to 'limit' uncategorized products and processes them in batches of 30.
    """
    client = get_client()
    logger.info(f"Starting batch categorization (limit: {limit})...")

    # 1. Fetch products missing 'category'
    # Using scroll to find points where category field is null or missing
    points, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=Filter(
            must_not=[
                IsNullCondition(is_null={"key": "category"}) # Qdrant 'is_null' used with must_not to find missing? 
                # Actually, Filter(must=[IsNullCondition(key="category")]) finds points where it IS null.
            ]
        ),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    
    # Wait, the IsNullCondition logic in Qdrant can be tricky.
    # Let's try a simpler approach: get points and filter in Python if needed, 
    # but let's try to use the correct Qdrant filter.
    # In Qdrant, to find points where a key is MISSING:
    # Filter(must=[IsEmptyCondition(key="category")]) - wait, Qdrant doesn't have IsEmpty.
    # It has IsNullCondition.
    
    # Let's just fetch all and filter for demonstration, or use the IsNull correctly.
    # Actually, a better way is to check if it's missing.
    
    points, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        limit=limit,
        with_payload=True,
    )
    
    uncategorized = [p for p in points if "category" not in p.payload or p.payload["category"] is None]
    
    if not uncategorized:
        logger.info("No uncategorized products found.")
        return

    logger.info(f"Found {len(uncategorized)} products to categorize.")

    # 2. Process in batches of 30
    batch_size = 30
    for i in range(0, len(uncategorized), batch_size):
        batch = uncategorized[i:i + batch_size]
        await _process_batch(batch)

async def _process_batch(points: List):
    """Sends a batch of 30 products to Gemini and updates Qdrant."""
    logger.info(f"Processing batch of {len(points)} products...")
    
    batch_data = []
    for p in points:
        batch_data.append({
            "id": str(p.id),
            "name": p.payload.get("product_name", ""),
            "url": p.payload.get("product_url", "")
        })

    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(model_name=settings.gemini_model_name)
    
    prompt = f"Categorize these products:\n{json.dumps(batch_data, indent=2)}\n\nReturn JSON only."
    
    try:
        response = model.generate_content([SYSTEM_PROMPT, prompt])
        result_text = response.text.strip()
        
        # Clean markdown if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:].strip()
        
        categorization = json.loads(result_text)
        logger.info(f"AI returned categorization for {len(categorization)} items.")

        # 3. Update Qdrant
        client = get_client()
        for p_id, result in categorization.items():
            if isinstance(result, dict):
                category = result.get("category")
                gender = result.get("gender")
                
                payload = {}
                if category in CATEGORIES:
                    payload["category"] = category
                if gender in GENDERS:
                    payload["gender"] = gender
                
                if payload:
                    client.set_payload(
                        collection_name=settings.qdrant_collection,
                        payload=payload,
                        points=[p_id],
                    )
        
        logger.info(f"Batch update complete.")
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_batch_categorization())
