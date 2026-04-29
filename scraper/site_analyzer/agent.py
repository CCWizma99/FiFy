"""
scraper/site_analyzer/agent.py
Site Analyzer Agent — uses Claude to inspect raw HTML and generate
a JSON scraping configuration for a given retail site.
"""
import json
from pathlib import Path

import google.generativeai as genai

from backend.config import settings
from backend.utils.logger import get_logger
from scraper.site_analyzer.prompt_templates import (
    SITE_ANALYZER_SYSTEM_PROMPT,
    SITE_ANALYZER_USER_PROMPT,
)

logger = get_logger(__name__)
CONFIGS_DIR = Path("scraper/configs")


def analyze_site(
    site_domain: str,
    listing_html: str,
    detail_html: str,
    card_html: str = "",
    confirmed_listing_url: str = "",
) -> dict:
    """
    Send truncated HTML to Gemini and get back a JSON scraping config.
    Saves the config to scraper/configs/<site>.json for reuse.
    confirmed_listing_url: the URL we actually navigated to and confirmed had products.
    This overrides whatever the AI generates for listing_url_pattern.
    """
    logger.info(f"Analyzing site with AI: {site_domain}")
    logger.info(f"Using model: {settings.gemini_model_name}")

    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(
        model_name=settings.gemini_model_name,
        system_instruction=SITE_ANALYZER_SYSTEM_PROMPT,
    )

    user_message = SITE_ANALYZER_USER_PROMPT.format(
        listing_html=listing_html[:15000],
        detail_html=detail_html[:10000],
        card_html=card_html[:3000] if card_html else "(not available)",
        site_domain=site_domain,
    )
    
    logger.info(f"Sending prompt to Gemini ({len(user_message)} chars)…")

    try:
        response = model.generate_content(user_message)
        logger.info("Gemini response received.")
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise

    # Gemini might wrap JSON in code blocks
    raw_text = response.text.strip()
    logger.debug(f"Raw Gemini response: {raw_text[:500]}…")
    
    if raw_text.startswith("```json"):
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    try:
        config = json.loads(raw_text)
    except json.JSONDecodeError as je:
        logger.error(f"Failed to parse JSON from Gemini response: {je}")
        logger.error(f"Full problematic response: {raw_text}")
        raise

    # --- POST-PROCESSING: fix known AI failure patterns ---

    # 1. Always trust the URL we actually confirmed had product cards, not the AI's guess
    if confirmed_listing_url:
        ai_url = config.get("listing_url_pattern", "")
        if ai_url != confirmed_listing_url:
            logger.info(f"Overriding AI listing_url '{ai_url}' with confirmed URL: {confirmed_listing_url}")
        config["listing_url_pattern"] = confirmed_listing_url

    # 2. Sanitize field selectors
    config["fields"] = _sanitize_fields(config.get("fields", {}))

    # 3. Safeguard: Don't save if listing_html is suspiciously small (likely an error page)
    if len(listing_html) < 10000:
        logger.warning(f"Listing HTML for {site_domain} is suspiciously small ({len(listing_html)} chars). Config will NOT be saved to disk.")
        return config

    _save_config(site_domain, config)
    logger.info(f"Config generated and saved for {site_domain}")
    logger.info(f"--- GENERATED CONFIG FOR {site_domain} ---\n{json.dumps(config, indent=2)}\n--- END CONFIG ---")
    return config


def _sanitize_fields(fields: dict) -> dict:
    """Fix known AI failure patterns in field selectors."""
    sanitized = {}
    GENERIC_CLASSES = [".flex", ".col", ".gap", ".items-", ".justify-", ".w-full", ".h-full", ".relative", ".absolute", ".group"]
    
    for key, selector in fields.items():
        if not selector:
            sanitized[key] = selector
            continue

        # Ban CSS4 pseudo-classes that Playwright's query_selector doesn't support
        if any(bad in selector for bad in [":has(", ":is(", ":has-text(", ":contains("]):
            if key == "product_url":
                sanitized[key] = "a[href*='/product/']"
                logger.warning(f"Replaced unsupported pseudo-class in '{key}': '{selector}' → '{sanitized[key]}'")
            else:
                sanitized[key] = selector.split(":")[0] or selector  # Strip the pseudo-class
                logger.warning(f"Stripped unsupported pseudo-class from '{key}': '{selector}' → '{sanitized[key]}'")
            continue

        # Strip extremely generic Tailwind utility classes from chains
        if "." in selector:
            parts = selector.split(".")
            base_tag = parts[0]
            classes = parts[1:]
            
            # If the chain is long, strip the generic ones
            if len(classes) > 2:
                filtered_classes = [c for c in classes if not any(g in f".{c}" for g in GENERIC_CLASSES)]
                if filtered_classes:
                    new_selector = f"{base_tag}.{'.'.join(filtered_classes)}"
                    if new_selector != selector:
                        logger.info(f"Stripped generic classes from '{key}': '{selector}' → '{new_selector}'")
                        selector = new_selector

        # Simplify absurdly long selectors
        if key == "image_url" and len(selector) > 50:
            sanitized[key] = "img"
            logger.warning(f"Simplified oversized image selector: '{selector[:50]}...' → '{sanitized[key]}'")
            continue

        sanitized[key] = selector
    return sanitized


def load_config(site_domain: str) -> dict | None:
    """Load a cached scraping config from disk. Returns None if not found."""
    config_path = CONFIGS_DIR / f"{site_domain.replace('.', '_')}.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return None


def _save_config(site_domain: str, config: dict) -> None:
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    config_path = CONFIGS_DIR / f"{site_domain.replace('.', '_')}.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
