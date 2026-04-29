"""
embeddings/text_embedder.py
Converts a text string to a 512-dim CLIP text vector.

Integration contract:
  Input:  str  (product name + category, or user query — max ~77 tokens)
  Output: list[float]  (512 dimensions)
"""
import torch
import torch.nn.functional as F

from embeddings.clip_model import get_model


def embed_text(text: str) -> list[float]:
    """
    Generate a CLIP text embedding for a string.
    CLIP text encoder truncates at 77 tokens automatically.
    """
    model, processor = get_model()

    inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        result = model.get_text_features(**inputs)

        # Newer transformers versions return a model output object instead of a raw tensor.
        if isinstance(result, torch.Tensor):
            features = result
        elif hasattr(result, "pooler_output"):
            features = result.pooler_output
        else:
            features = result.last_hidden_state[:, 0, :]

        # Normalise to unit sphere for cosine similarity
        features = F.normalize(features, dim=-1)

    return features.squeeze().tolist()
