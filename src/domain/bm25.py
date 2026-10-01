"""Score chunks against a query with BM25."""

import math

from collections import Counter
from collections.abc import Iterable
from typing import NamedTuple


# The usual BM25 values, kept as they are on purpose: tuning them against
# datasets whose answers we know would inflate the metric and collapse on
# new data. Any calibration has to be measured and explained.
K1: float = 1.5
B: float = 0.75


class Bm25Index(NamedTuple):
    """Everything BM25 needs to score a chunk, counted once.

    A *document* here is a **chunk**, not a file: the chunk is what gets
    scored, ranked and returned as a source. ``df`` is not stored because it
    is how many chunks a term appears in, that is ``len(postings[term])``.

    The tuple cannot be reassigned, but the dictionaries it holds are
    ordinary ones: nothing modifies them once the index is built.

    Attributes:
        postings: Term to the chunks holding it and its frequency there.
        lengths: Chunk to its length in tokens.
        average_length: Mean chunk length in tokens, 0.0 for an empty corpus.
        document_count: How many chunks the index holds.
    """

    postings: dict[str, dict[int, int]]
    lengths: dict[int, int]
    average_length: float
    document_count: int


def build_index(documents: Iterable[tuple[int, list[str]]]) -> Bm25Index:
    """Count the corpus once, so that every query is cheap afterwards.

    The documents are walked exactly once, because an iterable may be a
    generator that a second pass would find empty.

    Args:
        documents: Pairs of chunk id and its tokens, already tokenized.

    Returns:
        The index, with zeros instead of a division by zero when the corpus
        holds no chunk.
    """
    postings: dict[str, dict[int, int]] = {}
    lengths: dict[int, int] = {}
    total_tokens: int = 0

    for chunk_id, tokens in documents:
        lengths[chunk_id] = len(tokens)
        total_tokens += len(tokens)

        for term, count in Counter(tokens).items():
            postings.setdefault(term, {})[chunk_id] = count

    document_count = len(lengths)
    average_length = total_tokens / document_count if document_count else 0.0
    return Bm25Index(
        postings=postings,
        lengths=lengths,
        average_length=average_length,
        document_count=document_count
    )


def idf(index: Bm25Index, term: str) -> float:
    """Weigh a term: the fewer chunks hold it, the more it tells us.

    A term absent from the corpus has ``df`` 0, which yields a high weight
    that costs nothing: no chunk will add it to its score. The ``0.5`` terms
    smooth the extremes and keep the denominator away from zero.

    Args:
        index: The built index.
        term: A single query term, already tokenized.

    Returns:
        The inverse document frequency of the term.
    """
    df = len(index.postings.get(term, {}))
    return math.log(1 + (index.document_count - df + 0.5) / (df + 0.5))


def rank(
    index: Bm25Index, query_tokens: list[str], k: int
) -> list[tuple[int, float]]:
    """Return the best ``k`` chunks for a query, best first.

    Only chunks holding at least one query term are scored, which is what
    makes a query cheap: the posting lists hand them over without touching
    the corpus. Ties are broken by chunk id so that the order never depends
    on how the index was built.

    Args:
        index: The built index.
        query_tokens: The query, already tokenized; repetitions are ignored
            because a term weighs the same however often it is asked for.
        k: Maximum number of results; 0 returns nothing.

    Returns:
        Pairs of chunk id and score, sorted by descending score and, on a
        tie, by ascending chunk id. Empty when no term is known.
    """
    scores: dict[int, float] = {}
    average_length = index.average_length

    for term in set(query_tokens):
        term_idf = idf(index, term)

        for chunk_id, tf in index.postings.get(term, {}).items():
            chunk_length = index.lengths[chunk_id]
            length_norm = K1 * (1 - B + B * chunk_length / average_length)
            contribution = term_idf * tf * (K1 + 1) / (tf + length_norm)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + contribution

    ordered = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    return ordered[:k]
