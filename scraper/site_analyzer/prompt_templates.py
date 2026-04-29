"""
scraper/site_analyzer/prompt_templates.py
Claude prompt templates for extracting CSS selectors from retail site HTML.
"""

SITE_ANALYZER_SYSTEM_PROMPT = """You are an expert web scraper and HTML analyst.
Your job is to inspect raw HTML from a fashion retail website and identify the exact
CSS selectors needed to extract product data.

You MUST respond with ONLY a valid JSON object — no explanation, no markdown fencing.
"""

SITE_ANALYZER_USER_PROMPT = """Analyze the following HTML from a fashion retail website.

LISTING PAGE HTML (truncated):
{listing_html}

PRODUCT DETAIL PAGE HTML (truncated):
{detail_html}

Extract CSS selectors for the following fields. Use the most robust, specific selectors
you can find (prefer data attributes over class names where available).

Return a JSON object with this exact structure:
{{
  "site": "{site_domain}",
  "listing_url_pattern": "a representative category listing URL",
  "pagination_selector": "CSS selector for the next-page or load-more button",
  "product_card_selector": "CSS selector that matches individual product tiles on the listing page",
  "fields": {{
    "name": "CSS selector for product name within a product card",
    "price": "CSS selector for price within a product card",
    "image_url": "CSS selector for the product image (img tag or background)",
    "product_url": "CSS selector for the link to the product detail page"
  }}
}}

If any field cannot be found, set its value to null.
"""
