"""
embeddings/image_embedder.py
Converts a PIL Image to a 512-dim CLIP image vector.

Integration contract:
  Input:  PIL.Image.Image (RGB)
  Output: list[float]  (512 dimensions)
"""
import torch
import torch.nn.functional as F
from PIL import Image

from embeddings.clip_model import get_model


def embed_image(image: Image.Image) -> list[float]:
    """
    Generate a CLIP image embedding for a PIL Image.
    The image is preprocessed (resized to 224x224, normalised) internally.
    """
    model, processor = get_model()

    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        result = model.get_image_features(**inputs)

        # Newer transformers versions return a model output object instead of a raw tensor.
        if isinstance(result, torch.Tensor):
            features = result
        elif hasattr(result, "pooler_output"):
            features = result.pooler_output
        else:
            # Last resort: grab the CLS token from the last hidden state
            features = result.last_hidden_state[:, 0, :]

        # Normalise to unit sphere for cosine similarity
        features = F.normalize(features, dim=-1)

    return features.squeeze().tolist()
