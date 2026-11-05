"""Tests for semantic retrieval: build the vector index and search it.

The real SQLite stores are reused with the fake embedder of
``test_embed_index``, so no test loads the 90 MB model.
"""

from pathlib import Path

import numpy as np
import pytest

from src.application.ports.embedder import Vectors
from src.application.use_cases.index_corpus import run_index
from src.application.use_cases.shared.retrieval import (
    load_semantic_index,
    search_semantic,
)
from src.domain.models import MinimalSource
from src.domain.semantic import SemanticIndex
from tests.application.test_embed_index import (
    CORPUS,
    STORE,
    VECTORS,
    FakeEmbedderLoader,
    build_index,
    embed,
)


class FixedEmbedder:
    """An embedder that returns one chosen vector, whatever the query."""

    def __init__(self, vector: Vectors) -> None:
        """Keep the vector every call will return.

        Args:
            vector: The unit vector to answer with.
        """
        self.vector = vector

    def embed(self, texts: list[str]) -> Vectors:
        """Return the fixed vector, once per text.

        Args:
            texts: The texts to embed.

        Returns:
            One row per text, all the fixed vector.
        """
        return np.array([self.vector for _ in texts], dtype=np.float32)


def test_load_semantic_index_pairs_each_chunk_with_a_vector(
    tmp_path: Path,
) -> None:
    """Every row of the matrix has a source, and the corpus files show up."""
    _, index_path, vectors_path = build_index(tmp_path)
    embed(index_path, vectors_path, FakeEmbedderLoader())

    index = load_semantic_index(
        str(index_path), str(vectors_path), STORE, VECTORS
    )

    assert index.matrix.shape[0] == len(index.sources) > 0
    assert all(
        source.file_path.endswith((".py", ".md"))
        for source in index.sources
    )


def test_load_semantic_index_without_vectors_asks_to_index(
    tmp_path: Path,
) -> None:
    """Searching by meaning before embedding says exactly what to run."""
    _, index_path, vectors_path = build_index(tmp_path)

    with pytest.raises(ValueError) as error:
        load_semantic_index(
            str(index_path), str(vectors_path), STORE, VECTORS
        )

    assert str(error.value) == (
        f"embeddings not found: {vectors_path}; run index --embeddings first"
    )


def test_load_semantic_index_with_stale_vectors_asks_to_index(
    tmp_path: Path,
) -> None:
    """Vectors of texts the index no longer has count as no vectors."""
    corpus, index_path, vectors_path = build_index(tmp_path)
    embed(index_path, vectors_path, FakeEmbedderLoader())
    for path in corpus.rglob("*.*"):
        path.write_text("# Changed\nEvery text is new now.\n")
    build_index_again(corpus, index_path)

    with pytest.raises(ValueError) as error:
        load_semantic_index(
            str(index_path), str(vectors_path), STORE, VECTORS
        )

    assert str(error.value) == (
        f"embeddings not found: {vectors_path}; run index --embeddings first"
    )


def build_index_again(corpus: Path, index_path: Path) -> None:
    """Re-index the corpus without embeddings, as a plain ``index`` does.

    Args:
        corpus: The corpus folder.
        index_path: The index file to rebuild.
    """
    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)


EAST = MinimalSource(
    file_path="east.md", first_character_index=0, last_character_index=0
)
NORTH = MinimalSource(
    file_path="north.md", first_character_index=0, last_character_index=0
)
INDEX = SemanticIndex(
    matrix=np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
    sources=[EAST, NORTH],
)


def test_search_semantic_embeds_the_query_and_ranks() -> None:
    """The query is embedded and the closest source comes first."""
    embedder = FixedEmbedder(np.array([1.0, 0.0], dtype=np.float32))

    results = search_semantic(INDEX, "how do I load it", 2, embedder)

    assert [source.file_path for source, _ in results] == [
        "east.md",
        "north.md",
    ]


def test_search_semantic_rejects_an_empty_query() -> None:
    """The same guard as the lexical search, before any embedding."""
    embedder = FixedEmbedder(np.array([1.0, 0.0], dtype=np.float32))

    with pytest.raises(ValueError) as error:
        search_semantic(INDEX, "   ", 2, embedder)

    assert str(error.value) == "query must not be empty"
