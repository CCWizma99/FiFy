"""
scraper/site_analyzer/agent.py
Site Analyzer Agent — uses Gemini to inspect raw HTML and generate
a JSON scraping configuration for a given retail site.
"""
import json
import re
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

# Playwright's querySelectorAll does not support these CSS4/non-standard pseudo-classes.
# They are valid in browsers but raise errors in Playwright — block them at the gate.
_UNSUPPORTED_PSEUDOS = (":has(", ":is(", ":has-text(", ":contains(", ":where(")

# Pure Tailwind/Bootstrap layout utilities that carry no semantic meaning.
# A selector made ONLY of these is noise — it will match hundreds of elements.
_LAYOUT_ONLY_CLASSES = frozenset([
    "flex", "grid", "block", "inline", "inline-block", "inline-flex",
    "col", "row", "container", "wrapper", "relative", "absolute", "fixed",
    "w-full", "h-full", "w-screen", "h-screen",
    "items-center", "items-start", "items-end",
    "justify-center", "justify-between", "justify-start", "justify-end",
    "gap-1", "gap-2", "gap-3", "gap-4", "gap-6", "gap-8",
    "p-0", "p-1", "p-2", "p-3", "p-4", "m-0", "m-auto",
    "overflow-hidden", "overflow-auto",
    "text-sm", "text-base", "text-lg", "text-xl",
    "font-medium", "font-semibold", "font-bold",
    "rounded", "rounded-md", "rounded-lg", "rounded-full",
    "bg-white", "bg-gray-100", "bg-transparent",
    "cursor-pointer", "select-none",
    "transition", "duration-200", "duration-300", "ease-in-out",
    "hover:scale-105", "hover:opacity-80", "group", "group-hover:opacity-100",
    "md:flex", "lg:flex", "sm:hidden", "md:hidden", "lg:block",
])


def analyze_site(
    site_domain: str,
    listing_html: str,
    detail_html: str,
    card_html: str = "",
    confirmed_listing_url: str = "",
) -> dict:
    """
    Send truncated HTML to Gemini and get back a JSON scraping config.
    Saves the config as a variant in the site's profile.
    """
    logger.info(f"Analyzing site with AI: {site_domain}")
    logger.info(f"Using model: {settings.gemini_model_name}")

    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(
        model_name=settings.gemini_model_name,
        system_instruction=SITE_ANALYZER_SYSTEM_PROMPT,
    )

    user_message = SITE_ANALYZER_USER_PROMPT.format(
        site_domain=site_domain,
        card_html=card_html[:10000] if card_html else "(not provided — infer from listing HTML)",
        listing_html=listing_html[:60000],
        detail_html=detail_html[:30000],
    )

    logger.info(f"Sending prompt to Gemini…")

    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(user_message)
            logger.info(f"Gemini response received.")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep((attempt + 1) * 5)
                continue
            else:
                logger.error(f"Gemini API call failed: {e}")
                raise

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        raw_text = raw_text.strip()

    try:
        config = json.loads(raw_text)
    except json.JSONDecodeError as je:
        logger.error(f"Failed to parse Gemini JSON: {je}")
        raise

    # ── POST-PROCESSING ────────────────────────────────────────────────────────
    if confirmed_listing_url:
        config["listing_url_pattern"] = confirmed_listing_url

    config = _sanitize_config(config)
    config["fields"] = _remove_unsupported_selectors(config.get("fields", {}))
    _warn_layout_only_selectors(config.get("fields", {}), site_domain)

    # ── SAVE AS VARIANT ────────────────────────────────────────────────────────
    if len(listing_html) >= 5_000:
        save_variant(site_domain, config, confirmed_listing_url)
    else:
        logger.warning(f"[{site_domain}] Listing HTML suspiciously small. Config not cached.")

    return config


def _remove_unsupported_selectors(fields: dict) -> dict:
    cleaned = {}
    for key, selector in fields.items():
        if not selector:
            cleaned[key] = selector
            continue
        if any(pseudo in selector for pseudo in _UNSUPPORTED_PSEUDOS):
            logger.warning(f"Dropping unsupported selector for '{key}': '{selector}'")
            cleaned[key] = None
        else:
            cleaned[key] = selector
    return cleaned


def _warn_layout_only_selectors(fields: dict, site_domain: str) -> None:
    for key, selector in fields.items():
        if not selector: continue
        classes_in_selector = re.findall(r"\.([^\s.#\[>+~:]+)", selector)
        if classes_in_selector and all(c in _LAYOUT_ONLY_CLASSES for c in classes_in_selector):
            logger.warning(f"[{site_domain}] Selector for '{key}' is layout-only: '{selector}'")


def _sanitize_config(config: dict) -> dict:
    if config.get("product_card_selector"):
        config["product_card_selector"] = _sanitize_selector(config["product_card_selector"])
    if config.get("pagination_selector"):
        config["pagination_selector"] = _sanitize_selector(config["pagination_selector"])
    if "fields" in config:
        for key in config["fields"]:
            config["fields"][key] = _sanitize_selector(config["fields"][key])
    return config


def _sanitize_selector(selector: str | None) -> str | None:
    if not selector or not isinstance(selector, str):
        return selector
    def escape_brackets(match):
        segment = match.group(0)
        brackets_content = re.search(r'\[([^\]]+)\]', segment)
        if brackets_content and '=' in brackets_content.group(1):
            return segment
        return segment.replace('[', r'\[').replace(']', r'\]').replace(r'\\\[', r'\[').replace(r'\\\]', r'\]')
    return re.sub(r'\.[^\s#:>+~]*\[[^\]\s#:>+~]+\][^\s#:>+~]*', escape_brackets, selector)


def load_config(site_domain: str) -> dict | None:
    """
    Load a site's configuration profile. 
    Returns a dict containing a 'variants' list.
    """
    config_path = CONFIGS_DIR / f"{site_domain.replace('.', '_')}.json"
    if not config_path.exists():
        return None
    
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        # Migration logic
        if "variants" not in data:
            logger.info(f"Migrating legacy config for {site_domain}")
            legacy_variant = {
                "id": "legacy_primary",
                "sample_url": data.get("listing_url_pattern", ""),
                "product_card_selector": data.get("product_card_selector"),
                "pagination_selector": data.get("pagination_selector"),
                "fields": data.get("fields", {})
            }
            data = {"site_domain": site_domain, "variants": [legacy_variant]}
            _write_to_disk(site_domain, data)
        return data
    except Exception as e:
        logger.error(f"Failed to load config for {site_domain}: {e}")
        return None


def save_variant(site_domain: str, new_config: dict, sample_url: str = ""):
    """Add a new layout variant to a site's profile."""
    profile = load_config(site_domain)
    if not profile:
        profile = {"site_domain": site_domain, "variants": []}
    
    new_fields = new_config.get("fields", {})
    new_card_sel = new_config.get("product_card_selector")
    
    for v in profile["variants"]:
        if v.get("fields") == new_fields and v.get("product_card_selector") == new_card_sel:
            return

    variant_id = f"v{len(profile['variants']) + 1}"
    variant = {
        "id": variant_id,
        "sample_url": sample_url or new_config.get("listing_url_pattern", ""),
        "product_card_selector": new_card_sel,
        "pagination_selector": new_config.get("pagination_selector"),
        "fields": new_fields
    }
    profile["variants"].append(variant)
    _write_to_disk(site_domain, profile)
    logger.info(f"Saved variant '{variant_id}' for {site_domain}")


def _write_to_disk(site_domain: str, data: dict):
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    config_path = CONFIGS_DIR / f"{site_domain.replace('.', '_')}.json"
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")