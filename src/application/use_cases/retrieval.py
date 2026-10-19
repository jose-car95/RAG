"""Shared retrieval steps: load the index once, search it many times.

Loading is kept apart from searching because building the index costs about
a second: a single query pays it once, and a whole dataset pays it once for
all its questions. Rebuilding it per question would need 184 s for 200
questions, well over the 90 s the subject allows.

This module holds what both use cases share, so that neither
``search`` nor ``search_dataset`` depends on the other.
"""

from typing import NamedTuple

from src.application.ports.index_store import IndexStore
from src.domain.bm25 import Bm25Index, build_index, rank
from src.domain.models import MinimalSource
from src.domain.tokenizer import tokenize


class CorpusIndex(NamedTuple):
    """The searchable corpus: BM25 counts plus where each chunk lives.

    The two travel together because a ranking returns chunk ids, and the
    caller needs a ``file_path`` and a character range to report a source.

    Attributes:
        bm25: Term counts and lengths, everything the formula needs.
        locations: Chunk id to its file path and character range.
    """

    bm25: Bm25Index
    locations: dict[int, tuple[str, int, int]]


def load_index(index_path: str, index_store: IndexStore) -> CorpusIndex:
    """Read the stored index once and prepare it for searching.

    Args:
        index_path: Where the index built by ``index`` lives.
        index_store: Reads the stored chunks.

    Returns:
        The corpus, ready for any number of searches.

    Raises:
        ValueError: If the index does not exist or cannot be read.
    """
    rows = index_store.load_chunks(index_path)
    index = build_index(
        (chunk_id, tokenize(text)) for chunk_id, _, _, _, text in rows
    )
    locations = {
        chunk_id: (file_path, first_index, last_index)
        for chunk_id, file_path, first_index, last_index, _ in rows
    }
    return CorpusIndex(
        bm25=index,
        locations=locations
    )


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
