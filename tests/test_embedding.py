"""
tests/test_embedding.py
Sanity checks for the CLIP embedding engine.
Verifies output shape, value range, and that image/text vectors are comparable.
"""
import pytest
from PIL import Image
import numpy as np

from embeddings.image_embedder import embed_image
from embeddings.text_embedder import embed_text


def _make_dummy_image() -> Image.Image:
    return Image.new("RGB", (224, 224), color=(128, 64, 32))


def test_image_embedding_shape():
    img = _make_dummy_image()
    vector = embed_image(img)
    assert isinstance(vector, list)
    assert len(vector) == 512, f"Expected 512 dims, got {len(vector)}"


def test_text_embedding_shape():
    vector = embed_text("red floral summer dress")
    assert isinstance(vector, list)
    assert len(vector) == 512

def test_embeddings_are_unit_vectors():
    """CLIP embeddings should be L2-normalised (norm ≈ 1.0)."""
    img_vec = embed_image(_make_dummy_image())
    txt_vec = embed_text("floral dress")
    assert abs(np.linalg.norm(img_vec) - 1.0) < 1e-5
    assert abs(np.linalg.norm(txt_vec) - 1.0) < 1e-5


def test_similar_texts_have_high_cosine_similarity():
    v1 = np.array(embed_text("red dress"))
    v2 = np.array(embed_text("crimson gown"))
    v3 = np.array(embed_text("men's hiking boots"))
    sim_similar = float(np.dot(v1, v2))
    sim_dissimilar = float(np.dot(v1, v3))
    assert sim_similar > sim_dissimilar, "Similar fashion items should have higher similarity"
