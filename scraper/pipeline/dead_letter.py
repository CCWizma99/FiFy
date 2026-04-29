"""
scraper/pipeline/dead_letter.py
Dead letter queue — products that fail validation are logged here.
A separate retry job re-attempts them once after 24 hours.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.utils.logger import get_logger

logger = get_logger(__name__)
DEAD_LETTER_PATH = Path("data/dead_letter.log")


def log_dead_letter(product: dict, reason: str) -> None:
    """Append a failed product to the dead letter log."""
    DEAD_LETTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "product_url": product.get("product_url"),
        "source_site": product.get("source_site"),
        "retry_after": None,  # Set by retry job
        "retried": False,
    }
    with open(DEAD_LETTER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    logger.warning("Dead letter: %s | reason: %s", product.get("product_url"), reason)


def load_dead_letters() -> list[dict]:
    """Load all entries from the dead letter log."""
    if not DEAD_LETTER_PATH.exists():
        return []
    entries = []
    with open(DEAD_LETTER_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries
