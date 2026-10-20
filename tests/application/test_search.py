"""Tests for the search use case: one query against the stored index."""

from pathlib import Path
from typing import cast

import pytest

from src.adapters.outbound.corpus import FileCorpus
from src.adapters.outbound.sqlite_index import SqliteIndexStore
from src.application.use_cases.index_corpus import run_index
from src.application.use_cases.search import run_search

CORPUS = FileCorpus()
STORE = SqliteIndexStore()
PY_FILE = (
    "def load_lora_adapter() -> None:\n"
    "    \"\"\"Load a lora adapter dynamically.\"\"\"\n"
    "    return None\n"
)
MD_FILE = "# Endpoints\nThe http endpoint loads a lora adapter.\n"


def make_index(tmp_path: Path) -> tuple[Path, Path]:
    """Build a tiny index and return the corpus and index paths.

    Args:
        tmp_path: Temporary folder provided by pytest.

    Returns:
        The corpus directory and the index file.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.py").write_text(PY_FILE, encoding="utf-8")
    (corpus / "b.md").write_text(MD_FILE, encoding="utf-8")
    index_path = tmp_path / "processed" / "index.db"
    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)
    return corpus, index_path


def test_search_returns_the_chunk_holding_the_query_terms(
    tmp_path: Path
) -> None:
    """The best source points at the file that talks about endpoints."""
    _, index_path = make_index(tmp_path)

    results = run_search("http endpoint", 5, str(index_path), STORE)

    assert results, "the corpus holds those terms"
    best_source, best_score = results[0]
    assert best_source.file_path.endswith("b.md")
    assert best_score > 0
    assert best_source.first_character_index < best_source.last_character_index


@pytest.mark.parametrize(
    "query", ["", "   ", "\n\t"], ids=["empty", "spaces", "whitespace"]
)
def test_an_empty_query_is_rejected(tmp_path: Path, query: str) -> None:
    """A query with no characters to search for is a user error.

    Args:
        tmp_path: Temporary folder provided by pytest.
        query: A query that holds nothing to search for.
    """
    _, index_path = make_index(tmp_path)

    with pytest.raises(ValueError, match="^query must not be empty$"):
        run_search(query, 5, str(index_path), STORE)


@pytest.mark.parametrize(
    "k",
    [0, -3, "abc", 2.5, True],
    ids=["zero", "negative", "text", "float", "bool"],
)
def test_an_invalid_k_is_rejected(tmp_path: Path, k: object) -> None:
    """``k`` must be a positive integer, as in ``search_dataset``.

    Args:
        tmp_path: Temporary folder provided by pytest.
        k: A rejected value, as Fire would pass it.
    """
    _, index_path = make_index(tmp_path)

    with pytest.raises(ValueError, match="^k must be a positive integer$"):
        run_search("lora", cast(int, k), str(index_path), STORE)


def test_a_missing_index_is_reported_and_creates_no_file(
    tmp_path: Path
) -> None:
    """Searching without an index explains what to do and leaves no file.

    ``sqlite3.connect`` creates the file it cannot find, so ``load_chunks`` has
    to check for it beforehand instead of leaving an empty database behind.
    """
    index_path = tmp_path / "processed" / "index.db"
    message = f"^index not found: {index_path}; run index first$"

    with pytest.raises(ValueError, match=message):
        run_search("lora", 5, str(index_path), STORE)

    assert not index_path.exists()
