"""
embeddings/image_embedder.py
Converts a PIL Image to a 512-dim CLIP image vector.

Integration contract:
  Input:  PIL.Image.Image (RGB)
  Output: list[float]  (512 dimensions)
"""
import torch
from PIL import Image

from embeddings.clip_model import get_model


def embed_image(image: Image.Image) -> list[float]:
    """
    Generate a CLIP image embedding for a PIL Image.
    The image is preprocessed (resized to 224×224, normalised) internally.
    """
    model, processor = get_model()

    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        # Normalise to unit sphere for cosine similarity
        features = features / features.norm(dim=-1, keepdim=True)

    return features.squeeze().tolist()
