"""Tests for storing one embedding per chunk text next to the lexical index.

The model is a fake that turns each text into a small vector, so the tests
check what is embedded and stored without loading MiniLM.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np
import pytest

from src.adapters.outbound.sqlite_vectors import SqliteVectorStore
from src.application.ports.embedder import Vectors
from src.application.use_cases.embed_index import run_embed_index
from src.domain.semantic import text_hash
from src.application.use_cases.index_corpus import run_index
from tests.application.test_index_corpus import (
    CORPUS,
    STORE,
    make_corpus,
    read_rows,
)

VECTORS = SqliteVectorStore()


class FakeEmbedder:
    """Stands in for MiniLM: a vector from the length of each text."""

    def __init__(self) -> None:
        """Start with no texts embedded."""
        self.texts: list[str] = []

    def embed(self, texts: list[str]) -> Vectors:
        """Record the texts and give each one a two-number vector.

        Args:
            texts: The texts to embed.

        Returns:
            One float32 row per text.
        """
        self.texts.extend(texts)
        return np.array(
            [[float(len(text)), 1.0] for text in texts], dtype=np.float32
        )


class FakeEmbedderLoader:
    """Hands out one ``FakeEmbedder`` and counts how often it is loaded."""

    def __init__(self) -> None:
        """Create the embedder, not loaded yet."""
        self.embedder = FakeEmbedder()
        self.loads = 0

    def __call__(self) -> FakeEmbedder:
        """Load the fake model.

        Returns:
            The fake embedder.
        """
        self.loads += 1
        return self.embedder


def build_index(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Index the small corpus of ``test_index_corpus``.

    Args:
        tmp_path: Temporary folder provided by pytest.

    Returns:
        The corpus folder, the index file and the vectors file.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    index_path = tmp_path / "processed" / "index.db"
    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)
    return corpus, index_path, tmp_path / "processed" / "embeddings.db"


def chunk_hashes(index_path: Path) -> set[str]:
    """Hash the text of every chunk in the index.

    Args:
        index_path: The index file.

    Returns:
        The distinct text hashes.
    """
    return {text_hash(text) for *_, text in read_rows(index_path)}


def embed(index_path: Path, vectors_path: Path,
          loader: FakeEmbedderLoader) -> tuple[int, int]:
    """Run the use case with the real stores and a fake model.

    Args:
        index_path: The index file.
        vectors_path: The vectors file.
        loader: The fake model loader.

    Returns:
        New vectors and distinct chunk texts.
    """
    return run_embed_index(
        str(index_path), str(vectors_path), STORE, VECTORS, loader
    )


def test_every_chunk_text_gets_a_vector(tmp_path: Path) -> None:
    """One stored vector per distinct chunk text, keyed by its hash."""
    _, index_path, vectors_path = build_index(tmp_path)
    loader = FakeEmbedderLoader()

    new, total = embed(index_path, vectors_path, loader)

    hashes = chunk_hashes(index_path)
    assert (new, total) == (len(hashes), len(hashes))
    assert VECTORS.known_hashes(str(vectors_path)) == hashes
    assert loader.loads == 1


def test_known_texts_are_not_embedded_again(tmp_path: Path) -> None:
    """A second run finds every vector and never loads the model."""
    _, index_path, vectors_path = build_index(tmp_path)
    embed(index_path, vectors_path, FakeEmbedderLoader())
    loader = FakeEmbedderLoader()

    new, total = embed(index_path, vectors_path, loader)

    assert (new, total) == (0, len(chunk_hashes(index_path)))
    assert loader.loads == 0


def test_a_changed_file_embeds_only_its_new_texts(tmp_path: Path) -> None:
    """Texts that did not change keep the vector they already have."""
    corpus, index_path, vectors_path = build_index(tmp_path)
    embed(index_path, vectors_path, FakeEmbedderLoader())
    before = chunk_hashes(index_path)
    (corpus / "b.md").write_text("# A\nnew words\n", encoding="utf-8")
    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)
    loader = FakeEmbedderLoader()

    new, _ = embed(index_path, vectors_path, loader)

    added = chunk_hashes(index_path) - before
    assert new == len(added)
    assert {text_hash(text) for text in loader.embedder.texts} == added


def test_vectors_are_stored_as_float32(tmp_path: Path) -> None:
    """The stored bytes give back exactly the vector the model returned."""
    _, index_path, vectors_path = build_index(tmp_path)
    loader = FakeEmbedderLoader()
    embed(index_path, vectors_path, loader)
    text = loader.embedder.texts[0]

    with closing(sqlite3.connect(vectors_path)) as connection:
        [(blob,)] = connection.execute(
            "SELECT vector FROM vectors WHERE text_hash = ?",
            (text_hash(text),)
        )

    stored = np.frombuffer(blob, dtype=np.float32)
    assert stored.tolist() == [float(len(text)), 1.0]


def test_a_missing_index_loads_no_model(tmp_path: Path) -> None:
    """Same message as the other commands, and no 90 MB model loaded."""
    index_path = tmp_path / "index.db"
    loader = FakeEmbedderLoader()

    with pytest.raises(ValueError) as error:
        embed(index_path, tmp_path / "embeddings.db", loader)

    assert str(error.value) == (
        f"index not found: {index_path}; run index first"
    )
    assert loader.loads == 0


def test_a_missing_vectors_file_knows_no_hash(tmp_path: Path) -> None:
    """Nothing embedded yet, and asking creates no file."""
    vectors_path = tmp_path / "nope" / "embeddings.db"

    assert VECTORS.known_hashes(str(vectors_path)) == set()
    assert not vectors_path.exists()


def test_load_vectors_gives_every_stored_vector_by_hash(
    tmp_path: Path
) -> None:
    """The round trip: what ``save_vectors`` wrote comes back unchanged."""
    _, index_path, vectors_path = build_index(tmp_path)
    loader = FakeEmbedderLoader()
    embed(index_path, vectors_path, loader)

    stored = VECTORS.load_vectors(str(vectors_path))

    assert set(stored) == VECTORS.known_hashes(str(vectors_path))
    text = loader.embedder.texts[0]
    assert stored[text_hash(text)].tolist() == [float(len(text)), 1.0]


def test_load_vectors_is_empty_when_there_is_no_file(tmp_path: Path) -> None:
    """A search before indexing embeddings finds no vectors, not an error."""
    assert VECTORS.load_vectors(str(tmp_path / "nope.db")) == {}
