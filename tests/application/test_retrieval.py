"""Tests for the index cache: build the index once, rebuild it when it changes.

The store is the real SQLite adapter with a counter on ``load_chunks``
(``CountingStore``), so the tests see how often the index is really read.
"""

from pathlib import Path

import pytest

from src.application.use_cases.index_corpus import run_index
from src.application.use_cases.retrieval import IndexCache, search_index
from tests.application.test_answer import CORPUS, STORE, make_index
from tests.application.test_search_dataset import CountingStore


def test_the_index_is_read_once_for_many_searches(tmp_path: Path) -> None:
    """A hit returns the index already built, without touching SQLite."""
    index_path = str(make_index(tmp_path))
    store = CountingStore()
    cache = IndexCache()

    first = cache.load(index_path, store)
    second = cache.load(index_path, store)

    assert store.loads == 1
    assert second is first


def test_a_rebuilt_index_is_read_again(tmp_path: Path) -> None:
    """``index`` changes the file, so the next load sees the new chunks."""
    index_path = make_index(tmp_path)
    store = CountingStore()
    cache = IndexCache()
    cache.load(str(index_path), store)
    corpus = tmp_path / "corpus"
    (corpus / "kv.md").write_text("# Cache\nThe kv cache blocks.\n")
    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)

    corpus_index = cache.load(str(index_path), store)

    assert store.loads == 2
    [(source, _)] = search_index(corpus_index, "kv cache blocks", 1)
    assert source.file_path == str(corpus / "kv.md")


def test_a_missing_index_is_reported_before_reading(tmp_path: Path) -> None:
    """Same message as the CLI, and nothing is read or kept."""
    index_path = tmp_path / "index.db"
    store = CountingStore()

    with pytest.raises(ValueError) as error:
        IndexCache().load(str(index_path), store)

    assert str(error.value) == (
        f"index not found: {index_path}; run index first"
    )
    assert store.loads == 0


def test_the_version_changes_when_the_index_is_rebuilt(
    tmp_path: Path
) -> None:
    """The cache key: modification time and size of the index file."""
    index_path = make_index(tmp_path)
    before = STORE.index_version(str(index_path))
    corpus = tmp_path / "corpus"
    (corpus / "kv.md").write_text("# Cache\nThe kv cache blocks.\n")

    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)

    assert STORE.index_version(str(index_path)) != before
