"""
tests/test_scraper.py
Tests for the Site Analyzer Agent and scraper config handling.
Uses mocked Gemini responses to avoid real API calls.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from scraper.site_analyzer.agent import analyze_site, load_config

MOCK_CONFIG = {
    "site": "test.com",
    "listing_url_pattern": "https://test.com/dresses",
    "pagination_selector": "button.load-more",
    "product_card_selector": "div.product-tile",
    "fields": {
        "name": "h2.product-name",
        "price": "span.price",
        "image_url": "img.product-img",
        "product_url": "a.product-link",
    },
}


def test_load_config_returns_none_for_unknown_site(tmp_path, monkeypatch):
    monkeypatch.setattr("scraper.site_analyzer.agent.CONFIGS_DIR", tmp_path)
    result = load_config("nonexistent.com")
    assert result is None


def test_analyze_site_saves_config(tmp_path, monkeypatch):
    monkeypatch.setattr("scraper.site_analyzer.agent.CONFIGS_DIR", tmp_path)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(MOCK_CONFIG))]

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = mock_response
        result = analyze_site("test.com", "<html>listing</html>", "<html>detail</html>")

    assert result["site"] == "test.com"
    saved_path = tmp_path / "test_com.json"
    assert saved_path.exists()


def test_load_config_reads_saved_config(tmp_path, monkeypatch):
    monkeypatch.setattr("scraper.site_analyzer.agent.CONFIGS_DIR", tmp_path)
    (tmp_path / "test_com.json").write_text(json.dumps(MOCK_CONFIG))
    result = load_config("test.com")
    assert result is not None
    assert result["site"] == "test.com"
