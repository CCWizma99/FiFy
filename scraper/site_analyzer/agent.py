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
) -> dict:
    """
    Send truncated HTML to Gemini and get back a JSON scraping config.
    Saves the config to scraper/configs/<site>.json for reuse.
    """
    logger.info("Analyzing site: %s", site_domain)

    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SITE_ANALYZER_SYSTEM_PROMPT,
    )

    user_message = SITE_ANALYZER_USER_PROMPT.format(
        listing_html=listing_html[:15000],   # Gemini has a larger context window
        detail_html=detail_html[:10000],
        site_domain=site_domain,
    )

    response = model.generate_content(user_message)
    
    # Gemini might wrap JSON in code blocks
    raw_text = response.text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    config = json.loads(raw_text)
    _save_config(site_domain, config)
    logger.info("Config generated and saved for %s", site_domain)
    return config


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
