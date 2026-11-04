"""Tests for hybrid retrieval: fuse BM25 and semantic with RRF.

The real SQLite stores are reused with the fake embedder of
``test_embed_index``, so no test loads the 90 MB model.
"""

from pathlib import Path

import pytest

from src.application.use_cases.search import run_hybrid_search
from src.domain.models import MinimalSource
from tests.application.test_embed_index import (
    STORE,
    VECTORS,
    FakeEmbedderLoader,
    build_index,
    embed,
)


def test_hybrid_search_returns_fused_sources_best_first(
    tmp_path: Path,
) -> None:
    """A valid query gives at most k sources, by descending fused score."""
    _, index_path, vectors_path = build_index(tmp_path)
    embed(index_path, vectors_path, FakeEmbedderLoader())

    results = run_hybrid_search(
        "first",
        2,
        str(index_path),
        str(vectors_path),
        STORE,
        VECTORS,
        FakeEmbedderLoader(),
    )

    assert 0 < len(results) <= 2
    assert all(isinstance(source, MinimalSource) for source, _ in results)
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_hybrid_search_fuses_both_retrievers(tmp_path: Path) -> None:
    """Sources from the lexical and the semantic lists both come through."""
    _, index_path, vectors_path = build_index(tmp_path)
    embed(index_path, vectors_path, FakeEmbedderLoader())

    results = run_hybrid_search(
        "first",
        10,
        str(index_path),
        str(vectors_path),
        STORE,
        VECTORS,
        FakeEmbedderLoader(),
    )

    files = {Path(source.file_path).name for source, _ in results}
    assert {"a.py", "b.md"} <= files


def test_hybrid_search_rejects_an_empty_query(tmp_path: Path) -> None:
    """The query is checked before any index, vector or model is touched."""
    _, index_path, vectors_path = build_index(tmp_path)
    loader = FakeEmbedderLoader()

    with pytest.raises(ValueError) as error:
        run_hybrid_search(
            "   ",
            2,
            str(index_path),
            str(vectors_path),
            STORE,
            VECTORS,
            loader,
        )

    assert str(error.value) == "query must not be empty"
    assert loader.loads == 0


def test_hybrid_search_rejects_k_of_zero(tmp_path: Path) -> None:
    """A non-positive k is rejected like any other search."""
    _, index_path, vectors_path = build_index(tmp_path)

    with pytest.raises(ValueError) as error:
        run_hybrid_search(
            "first",
            0,
            str(index_path),
            str(vectors_path),
            STORE,
            VECTORS,
            FakeEmbedderLoader(),
        )

    assert str(error.value) == "k must be a positive integer"


def test_hybrid_search_without_vectors_asks_to_index(tmp_path: Path) -> None:
    """Missing embeddings give the clear message and load no model."""
    _, index_path, vectors_path = build_index(tmp_path)
    loader = FakeEmbedderLoader()

    with pytest.raises(ValueError) as error:
        run_hybrid_search(
            "first",
            2,
            str(index_path),
            str(vectors_path),
            STORE,
            VECTORS,
            loader,
        )

    assert str(error.value) == (
        f"embeddings not found: {vectors_path}; run index --embeddings first"
    )
    assert loader.loads == 0
