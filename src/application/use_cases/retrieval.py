"""Shared retrieval steps: load the index once, search it many times.

Loading is kept apart from searching because building the index costs about
a second: a single query pays it once, and a whole dataset pays it once for
all its questions. Rebuilding it per question would need 184 s for 200
questions, well over the 90 s the subject allows.

This module holds what both use cases share, so that neither
``search`` nor ``search_dataset`` depends on the other.
"""

from collections.abc import Callable

import numpy as np

from src.application.indexing_code import code_version
from src.application.ports.embedder import Embedder
from src.application.ports.index_store import IndexStore
from src.application.ports.vector_store import VectorStore
from src.domain.bm25 import CorpusIndex, build_index, rank
from src.domain.models import MinimalSource
from src.domain.semantic import SemanticIndex, rank_semantic, text_hash
from src.domain.tokenizer import tokenize


def load_index(index_path: str, index_store: IndexStore) -> CorpusIndex:
    """Read the stored index once and prepare it for searching.

    Building it costs about 2 s, so the result is saved through the store
    and a later process loads it in about 0.2 s while both the index and the
    code that builds it are the same. The version is read before the chunks:
    if ``index`` runs meanwhile, the saved copy carries the old version and
    is simply rebuilt next time.

    Args:
        index_path: Where the index built by ``index`` lives.
        index_store: Reads the stored chunks.

    Returns:
        The corpus, ready for any number of searches.

    Raises:
        ValueError: If the index does not exist or cannot be read.
    """
    key = (index_store.index_version(index_path), code_version())
    built = index_store.load_built_index(index_path, key)
    if built is not None:
        return built
    rows = index_store.load_chunks(index_path)
    index = build_index(
        (chunk_id, tokenize(text)) for chunk_id, _, _, _, text in rows
    )
    locations = {
        chunk_id: (file_path, first_index, last_index)
        for chunk_id, file_path, first_index, last_index, _ in rows
    }
    corpus = CorpusIndex(bm25=index, locations=locations)
    index_store.save_built_index(index_path, key, corpus)
    return corpus


# Anything that turns a stored index into a searchable one: ``load_index``
# itself, or the ``load`` method of an ``IndexCache``.
IndexLoader = Callable[[str, IndexStore], CorpusIndex]


class IndexCache:
    """Keep the last built index and rebuild it only when the file changes.

    For long-lived processes such as the HTTP server: a CLI command lives for
    one query, so it has nothing to reuse. Each app owns its own cache, so
    there is no module-level state.

    ponytail: two requests that miss at the same time both build the index
    (about 2 s once, same result); a lock would avoid it if it ever matters.
    """

    def __init__(self) -> None:
        """Start empty: the first load always builds the index."""
        self._key: tuple[str, tuple[int, int]] | None = None
        self._corpus: CorpusIndex | None = None

    def load(self, index_path: str, index_store: IndexStore) -> CorpusIndex:
        """Return the built index, rebuilding it if the file changed.

        Args:
            index_path: Where the index lives.
            index_store: Reads the version and, on a miss, the chunks.

        Returns:
            The searchable index for ``index_path``.

        Raises:
            ValueError: If the index does not exist or cannot be read.
        """
        key = (index_path, index_store.index_version(index_path))
        if self._corpus is None or key != self._key:
            self._corpus = load_index(index_path, index_store)
            self._key = key
        return self._corpus


def validate_query_and_k(query: str, k: int) -> str:
    """Reject the arguments a search cannot work with.

    Lives here, and not in each caller, so that the two guards have a single
    implementation. ``run_search`` calls it before loading the index and
    ``search_index`` calls it again as the gate of any query: one
    implementation, two doorkeepers.

    Args:
        query: Question to search for, as it arrives from outside.
        k: Number of sources asked for.

    Returns:
        The query without the spaces around it, ready to tokenize.

    Raises:
        ValueError: If ``k`` is not a positive integer, or the query holds
            nothing but spaces.
    """
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k must be a positive integer")
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query must not be empty")
    return clean_query


def search_index(
    corpus: CorpusIndex,
    query: str,
    k: int
) -> list[tuple[MinimalSource, float]]:
    """Return the best ``k`` sources of a query, best first.

    Args:
        corpus: A corpus already loaded with ``load_index``.
        query: Question to search for; only spaces counts as empty.
        k: Maximum number of sources.

    Returns:
        Pairs of source and score, best first. Empty when no term of the
        query appears in the corpus.

    Raises:
        ValueError: If ``k`` is not a positive integer or the query is empty.
    """
    clean_query = validate_query_and_k(query, k)
    results = []
    for chunk_id, score in rank(corpus.bm25, tokenize(clean_query), k):
        file_path, first_index, last_index = corpus.locations[chunk_id]
        source = MinimalSource(
            file_path=file_path,
            first_character_index=first_index,
            last_character_index=last_index
        )
        results.append((source, score))

    return results


def load_semantic_index(
    index_path: str,
    vectors_path: str,
    index_store: IndexStore,
    vector_store: VectorStore
) -> SemanticIndex:
    """Build the semantic index: each chunk paired with its vector.

    Chunks share a vector when their text is equal, so a chunk is looked up
    by the hash of its text, the same key the indexer stored it under.

    Args:
        index_path: Where the chunks live.
        vectors_path: Where the vectors live.
        index_store: Reads the chunks.
        vector_store: Reads the vectors.

    Returns:
        The corpus as vectors, ready to search.

    Raises:
        ValueError: If no chunk of the index has a vector: nothing was
            embedded, or the vectors belong to texts the index no longer has.
    """
    vectors = vector_store.load_vectors(vectors_path)
    chunks = index_store.load_chunks(index_path)
    matrix_rows = []
    sources = []
    for _, file_path, first_index, last_index, text in chunks:
        key = text_hash(text)
        if key in vectors:
            matrix_rows.append(vectors[key])
            sources.append(
                MinimalSource(
                    file_path=file_path,
                    first_character_index=first_index,
                    last_character_index=last_index
                )
            )
    if not matrix_rows:
        raise ValueError(
            f"embeddings not found: {vectors_path}; "
            f"run index --embeddings first"
        )
    # ponytail: chunks without a vector (index newer than the embeddings) are
    # left out of the semantic search; index --embeddings fills them in.
    return SemanticIndex(matrix=np.stack(matrix_rows), sources=sources)


def search_semantic(
    index: SemanticIndex, query: str, k: int, embedder: Embedder
) -> list[tuple[MinimalSource, float]]:
    """Return the ``k`` sources closest in meaning to the query.

    Args:
        index: A semantic index built with ``load_semantic_index``.
        query: Question to search for; only spaces counts as empty.
        k: Maximum number of sources.
        embedder: Turns the query into a vector.

    Returns:
        Pairs of source and cosine score, best first.

    Raises:
        ValueError: If ``k`` is not a positive integer or the query is empty.
    """
    clean_query = validate_query_and_k(query, k)
    query_vector = embedder.embed([clean_query])[0]
    return rank_semantic(index, query_vector, k)
