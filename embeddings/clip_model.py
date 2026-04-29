"""
embeddings/clip_model.py
CLIP model loader — singleton pattern so the model is loaded once
into memory and reused for every embedding request.
"""
from transformers import CLIPProcessor, CLIPModel
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_model = None
_processor = None


def get_model():
    """Return the singleton CLIP model, loading it on first call."""
    global _model, _processor
    if _model is None:
        logger.info("Loading CLIP model: %s", settings.clip_model_name)
        _model = CLIPModel.from_pretrained(settings.clip_model_name)
        _processor = CLIPProcessor.from_pretrained(settings.clip_model_name)
        _model.eval()
        logger.info("CLIP model loaded.")
    return _model, _processor
