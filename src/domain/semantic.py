"""Semantic ranking: cosine similarity between a query and the chunks."""

import hashlib
from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

from src.domain.models import MinimalSource


def text_hash(text: str) -> str:
    """Name a chunk text by its SHA-256 hash.

    The vectors are stored under this key and looked up by it, so the
    indexer and the searcher must share this one function.

    Args:
        text: The chunk text.

    Returns:
        The hash in hexadecimal.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SemanticIndex(NamedTuple):
    """The corpus as vectors: one row per chunk, plus where each chunk is.

    The matrix and the sources travel together and share an order: row ``i``
    is the vector of ``sources[i]``.

    Attributes:
        matrix: One unit vector per chunk, stacked as rows.
        sources: The source of each row, in the same order.
    """

    matrix: NDArray[np.float32]
    sources: list[MinimalSource]


def rank_semantic(
    index: SemanticIndex, query_vector: NDArray[np.float32], k: int
) -> list[tuple[MinimalSource, float]]:
    """Return the ``k`` chunks whose meaning is closest to the query.

    The stored vectors and the query vector are already unit length, so the
    cosine of the angle between two of them is just their dot product. One
    matrix-vector product scores every chunk at once.

    Args:
        index: The corpus vectors and their sources.
        query_vector: The embedded query, unit length.
        k: Maximum number of sources.

    Returns:
        Pairs of source and cosine score, highest first. Empty when the
        index holds no vectors.
    """
    scores = index.matrix @ query_vector
    results = list(zip(index.sources, (float(score) for score in scores)))
    return sorted(results, key=lambda pair: -pair[1])[:k]
