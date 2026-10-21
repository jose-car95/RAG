"""Use case: search one query against the stored index."""

from src.application.ports.index_store import IndexStore
from src.application.use_cases.retrieval import (
    IndexLoader,
    load_index,
    search_index,
    validate_query_and_k
)
from src.domain.models import MinimalSource


def run_search(
    query: str, k: int, index_path: str, index_store: IndexStore,
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
