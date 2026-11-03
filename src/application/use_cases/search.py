"""Use case: search one query, by words (BM25) or by meaning (vectors)."""

from src.application.ports.embedder import EmbedderLoader
from src.application.ports.index_store import IndexStore
from src.application.ports.vector_store import VectorStore
from src.application.use_cases.retrieval import (
    IndexLoader,
    load_index,
    load_semantic_index,
    search_index,
    search_semantic,
    validate_query_and_k
)
from src.domain.models import MinimalSource


def run_search(
    query: str,
    k: int,
    index_path: str,
    index_store: IndexStore,
    load: IndexLoader = load_index
) -> list[tuple[MinimalSource, float]]:
    """Search one query; by default the index is built for this call alone.

    Args:
        query: Question to search for.
        k: Maximum number of sources.
        index_path: Where the index lives.
        index_store: Reads the stored chunks.
        load: Builds the searchable index; the API passes its cache.

    Returns:
        Pairs of source and score, best first.

    Raises:
        ValueError: If the arguments are invalid or the index cannot be read.
    """
    # Checked before loading, because building the index costs about a
    # second and a bad query or k does not deserve that work.
    validate_query_and_k(query, k)
    corpus = load(index_path, index_store)
    return search_index(corpus, query, k)


def run_semantic_search(
    query: str,
    k: int,
    index_path: str,
    vectors_path: str,
    index_store: IndexStore,
    vector_store: VectorStore,
    load_embedder: EmbedderLoader
) -> list[tuple[MinimalSource, float]]:
    """Search one query by meaning, with the vectors of ``index --embeddings``.

    Args:
        query: Question to search for.
        k: Maximum number of sources.
        index_path: Where the chunks live.
        vectors_path: Where the vectors live.
        index_store: Reads the stored chunks.
        vector_store: Reads the stored vectors.
        load_embedder: Loads the model that embeds the query.

    Returns:
        Pairs of source and cosine score, best first.

    Raises:
        ValueError: If the arguments are invalid, the index cannot be read or
            no chunk has a vector.
    """
    # Checked before loading, because the vectors and the model cost seconds
    # and a bad query or k does not deserve that work.
    validate_query_and_k(query, k)
    index = load_semantic_index(
        index_path, vectors_path, index_store, vector_store
    )
    return search_semantic(index, query, k, load_embedder())
