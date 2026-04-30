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
    Saves the config to scraper/configs/<site>.json for reuse.

    confirmed_listing_url: the URL we actually navigated to and confirmed had products.
    When provided, this always overrides the AI's listing_url_pattern guess.
    """
    logger.info(f"Analyzing site with AI: {site_domain}")
    logger.info(f"Using model: {settings.gemini_model_name}")

    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(
        model_name=settings.gemini_model_name,
        system_instruction=SITE_ANALYZER_SYSTEM_PROMPT,
    )

    # Log the sizes of the inputs (after minimization but before any truncation for the prompt)
    logger.info(
        f"AI Analysis Payload Preparation: "
        f"Listing={len(listing_html)} chars, "
        f"Detail={len(detail_html)} chars, "
        f"Card={len(card_html)} chars"
    )

    # We increase the limits now that we have a powerful minimizer. 
    # 60k for listing and 30k for detail is more than enough for minimized content.
    user_message = SITE_ANALYZER_USER_PROMPT.format(
        site_domain=site_domain,
        card_html=card_html[:10000] if card_html else "(not provided — infer from listing HTML)",
        listing_html=listing_html[:60000],
        detail_html=detail_html[:30000],
    )

    logger.info(f"Sending prompt to Gemini (Total Prompt Size: {len(user_message)} chars)…")

    try:
        response = model.generate_content(user_message)
        logger.info(f"Gemini response received ({len(response.text)} chars).")
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise

    raw_text = response.text.strip()
    logger.debug(f"RAW GEMINI RESPONSE:\n{raw_text}")

    # Strip markdown code fences if the model wrapped the JSON
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        raw_text = raw_text.strip()

    try:
        config = json.loads(raw_text)
    except json.JSONDecodeError as je:
        logger.error(f"Failed to parse Gemini JSON response: {je}")
        logger.error(f"Problematic text:\n{raw_text}")
        raise

    # ── POST-PROCESSING ────────────────────────────────────────────────────────
    # Each step below has a documented reason. We only override the AI when we
    # have a concrete fact it could not have known (e.g. the confirmed URL) or
    # when a selector would cause a hard Playwright crash (unsupported pseudo).

    # 1. Trust the URL we actually confirmed over the AI's inference from HTML.
    if confirmed_listing_url:
        ai_url = config.get("listing_url_pattern", "")
        if ai_url != confirmed_listing_url:
            logger.info(
                f"Overriding AI listing_url '{ai_url}' → confirmed: '{confirmed_listing_url}'"
            )
        config["listing_url_pattern"] = confirmed_listing_url

    # 2. Fix Tailwind-style unescaped brackets in selectors (e.g. .w-[10px] -> .w-\[10px\])
    # This prevents Playwright SyntaxErrors on sites using arbitrary Tailwind values.
    config = _sanitize_config(config)

    # 3. Remove selectors that Playwright cannot execute (hard crash prevention).
    #    We do NOT attempt to "fix" them — a broken selector is less dangerous
    #    than a silently wrong one. The scraper's fallback logic handles None.
    config["fields"] = _remove_unsupported_selectors(config.get("fields", {}))

    # 4. Warn (don't mutate) when a selector looks like pure layout utility noise.
    _warn_layout_only_selectors(config.get("fields", {}), site_domain)

    # ── VALIDATION WARNINGS ────────────────────────────────────────────────────
    if not config.get("fields", {}).get("price"):
        price_pattern = re.search(r"[\$£€][\d,]+|[\d,]+\s*(LKR|Rs|USD|INR)", card_html or "")
        if price_pattern:
            logger.warning(
                f"[{site_domain}] Price visible in card HTML ('{price_pattern.group()}') "
                f"but AI returned no price selector. Manual review needed."
            )
        else:
            logger.info(f"[{site_domain}] No price selector — no price detected in card HTML either.")

    if not config.get("product_card_selector"):
        logger.warning(f"[{site_domain}] AI returned no product_card_selector. Scraping will fail.")

    # ── SAVE TO DISK ───────────────────────────────────────────────────────────
    # Skip caching if the listing HTML is suspiciously small — it was likely
    # an error page, CAPTCHA, or redirect and the config is probably wrong.
    if len(listing_html) < 10_000:
        logger.warning(
            f"[{site_domain}] Listing HTML is only {len(listing_html)} chars — "
            f"possibly an error page. Config NOT cached to disk."
        )
    else:
        _save_config(site_domain, config)
        logger.info(f"Config cached: scraper/configs/{site_domain.replace('.', '_')}.json")

    logger.info(f"Final config for {site_domain}:\n{json.dumps(config, indent=2)}")
    return config


def _remove_unsupported_selectors(fields: dict) -> dict:
    """
    Drop any selector that uses pseudo-classes Playwright cannot execute.
    Returns None for affected fields so the scraper's fallback logic can handle them —
    we never silently substitute a guess, which could match the wrong element.
    """
    cleaned = {}
    for key, selector in fields.items():
        if not selector:
            cleaned[key] = selector
            continue
        if any(pseudo in selector for pseudo in _UNSUPPORTED_PSEUDOS):
            logger.warning(
                f"Dropping unsupported selector for '{key}': '{selector}' "
                f"(contains a pseudo-class Playwright cannot execute). "
                f"Set to None — scraper fallback will apply."
            )
            cleaned[key] = None
        else:
            cleaned[key] = selector
    return cleaned


def _warn_layout_only_selectors(fields: dict, site_domain: str) -> None:
    """
    Log a warning when a selector appears to be composed entirely of layout-
    utility classes (Tailwind / Bootstrap). These selectors are not wrong per se —
    sometimes a site has no semantic classes — but they are fragile and broad,
    so we surface them for human review rather than silently dropping them.
    """
    for key, selector in fields.items():
        if not selector:
            continue
        # Extract class names from the selector string
        classes_in_selector = re.findall(r"\.([^\s.#\[>+~:]+)", selector)
        if classes_in_selector and all(c in _LAYOUT_ONLY_CLASSES for c in classes_in_selector):
            logger.warning(
                f"[{site_domain}] Selector for '{key}' is composed entirely of "
                f"layout-utility classes: '{selector}'. "
                f"It may match many unintended elements — manual review recommended."
            )


def _sanitize_config(config: dict) -> dict:
    """Recursively sanitize all selectors in a config object."""
    if config.get("product_card_selector"):
        config["product_card_selector"] = _sanitize_selector(config["product_card_selector"])
    
    if config.get("pagination_selector"):
        config["pagination_selector"] = _sanitize_selector(config["pagination_selector"])

    if "fields" in config:
        for key in config["fields"]:
            config["fields"][key] = _sanitize_selector(config["fields"][key])
            
    return config


def _sanitize_selector(selector: str | None) -> str | None:
    """
    Escape square brackets in Tailwind-style class selectors (e.g. .w-[10px] -> .w-\[10px\])
    while preserving standard attribute selectors (e.g. div[data-id="1"]).
    """
    if not selector or not isinstance(selector, str):
        return selector
    
    # We look for segments starting with a dot (class) and containing brackets.
    # Standard attribute selectors [attr=val] do not start with a dot, so they are safe.
    def escape_brackets(match):
        segment = match.group(0)
        
        # Attribute selectors usually have '=' (like [type="text"])
        # Arbitrary Tailwind values usually do NOT have '=' (like [160px], [#fff])
        # If we see an '=', we assume it's a standard attribute selector and leave it alone.
        brackets_content = re.search(r'\[([^\]]+)\]', segment)
        if brackets_content and '=' in brackets_content.group(1):
            return segment
            
        # Escape [ and ] only if they aren't already escaped
        fixed = segment.replace('[', r'\[').replace(']', r'\]')
        # Clean up any resulting double-escapes
        fixed = fixed.replace(r'\\\[', r'\[').replace(r'\\\]', r'\]')
        return fixed

    # Regex: matches a dot followed by any non-whitespace, non-separator characters, 
    # as long as it contains at least one bracket.
    return re.sub(r'\.[^\s#:>+~]*\[[^\]\s#:>+~]+\][^\s#:>+~]*', escape_brackets, selector)


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