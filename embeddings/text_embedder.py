"""
embeddings/text_embedder.py
Converts a text string to a 512-dim CLIP text vector.

Integration contract:
  Input:  str  (product name + category, or user query — max ~77 tokens)
  Output: list[float]  (512 dimensions)
"""
import torch

from embeddings.clip_model import get_model


def embed_text(text: str) -> list[float]:
    """
    Generate a CLIP text embedding for a string.
    CLIP text encoder truncates at 77 tokens automatically.
    """
    model, processor = get_model()

    inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        features = model.get_text_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)

    return features.squeeze().tolist()
