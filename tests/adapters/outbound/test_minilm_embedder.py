"""Tests for the MiniLM embedder with the real model.

They need the weights in ``.cache/huggingface/`` (91 MB, not in the repo),
so they are marked slow and skipped when the model is not downloaded.
"""

import numpy as np
import pytest

from src.adapters.outbound.minilm_embedder import MODEL_NAME, load_embedder
from tests.adapters.outbound.test_qwen_generator import MODEL_FILES

MINILM_FILES = MODEL_FILES.parent / (
    "models--" + MODEL_NAME.replace("/", "--")
)

needs_model = pytest.mark.skipif(
    not MINILM_FILES.is_dir(), reason="all-MiniLM-L6-v2 not downloaded"
)


@pytest.mark.slow
@needs_model
def test_similar_texts_get_close_unit_vectors() -> None:
    """384 numbers of length 1; meaning, not shared words, sets closeness."""
    vectors = load_embedder().embed([
        "How do I load a LoRA adapter at runtime?",
        "Dynamically attach low-rank adaptation weights to a served model.",
        "The weather in Madrid is sunny today.",
    ])

    assert vectors.shape == (3, 384)
    assert vectors.dtype == np.float32
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)
    similar, unrelated = vectors[1] @ vectors[0], vectors[2] @ vectors[0]
    assert similar > unrelated
