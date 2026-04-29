"""
backend/config.py
Loads all configuration from environment variables via pydantic-settings.
All modules should import `settings` from here — never read os.environ directly.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "fashion_products"

    # Google Gemini (Site Analyzer Agent)
    google_api_key: str = ""

    # CLIP
    clip_model_name: str = "openai/clip-vit-base-patch32"

    # Scraper schedule
    scrape_interval_hours: int = 48
    dead_link_check_interval_hours: int = 24

    # Search
    max_results: int = 20

    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"


settings = Settings()
