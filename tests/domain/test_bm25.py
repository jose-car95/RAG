"""Tests for the BM25 index and the ranking it feeds."""

import math

import pytest

from src.domain.bm25 import IDF_FLOOR, K1, build_index, idf, rank

# A tiny corpus, with tokens as the tokenizer would produce them, so that every
# expected number can be checked by hand. Chunk 4 is empty on purpose: the real
# corpus holds chunks with no token at all.
DOCUMENTS: list[tuple[int, list[str]]] = [
    (1, ["lora", "adapter", "lora"]),
    (2, ["lora"]),
    (3, ["http", "endpoint"]),
    (4, []),
]


def test_postings_hold_the_frequency_of_each_term_in_each_chunk() -> None:
    """Each term maps to the chunks holding it and how many times."""
    index = build_index(DOCUMENTS)

    assert index.postings == {
        "lora": {1: 2, 2: 1},
        "adapter": {1: 1},
        "http": {3: 1},
        "endpoint": {3: 1},
    }


def test_the_index_describes_the_size_of_the_corpus() -> None:
    """Lengths, average length and document count come from the corpus."""
    index = build_index(DOCUMENTS)

    assert index.lengths == {1: 3, 2: 1, 3: 2, 4: 0}
    assert index.average_length == 1.5
    assert index.document_count == 4


def test_document_frequency_is_read_from_the_postings() -> None:
    """``df`` is not stored: it is how many chunks a term appears in."""
    index = build_index(DOCUMENTS)

    assert len(index.postings["lora"]) == 2
    assert len(index.postings["adapter"]) == 1


def test_an_empty_corpus_has_no_average_length() -> None:
    """An empty corpus yields zeros instead of dividing by zero."""
    index = build_index([])

    assert index.postings == {}
    assert index.lengths == {}
    assert index.average_length == 0.0
    assert index.document_count == 0


def test_documents_can_arrive_as_a_generator() -> None:
    """The corpus is streamed, so any iterable of pairs is accepted."""
    index = build_index(iter(DOCUMENTS))

    assert index.document_count == 4
    assert index.postings["lora"] == {1: 2, 2: 1}


def test_bm25_uses_the_original_okapi_k1() -> None:
    """The original Okapi BM25 value, not a tuned one."""
    assert K1 == 1.2


def test_idf_grows_as_a_term_gets_rarer() -> None:
    """A term in fewer chunks weighs more (original Robertson IDF)."""
    index = build_index(DOCUMENTS)

    # N=4. "adapter" is in 1 chunk: ln((4-1+0.5)/(1+0.5)) = ln(7/3).
    assert idf(index, "adapter") == pytest.approx(math.log(7 / 3))
    assert idf(index, "adapter") > idf(index, "lora")


def test_idf_of_an_unknown_term_does_not_fail() -> None:
    """A term absent from the corpus has df 0: ln(4.5/0.5) = ln(9)."""
    index = build_index(DOCUMENTS)

    assert idf(index, "kubernetes") == pytest.approx(math.log(9))


def test_a_term_in_half_the_chunks_gets_the_floor() -> None:
    """ln((4-2+0.5)/(2+0.5)) = ln(1) = 0, which is raised to the floor."""
    index = build_index(DOCUMENTS)

    assert idf(index, "lora") == IDF_FLOOR


def test_a_term_in_most_chunks_never_weighs_negative() -> None:
    """In 3 of 4 chunks the original IDF is ln(1.5/3.5) < 0 (decision C)."""
    index = build_index(
        [(1, ["def"]), (2, ["def"]), (3, ["def"]), (4, ["lora"])]
    )

    assert idf(index, "def") == IDF_FLOOR


def test_the_floor_is_tiny_but_positive() -> None:
    """Positive so it still breaks ties, tiny so it barely counts."""
    assert 0 < IDF_FLOOR <= 1e-6


def test_a_rare_term_outranks_a_common_one() -> None:
    """Chunk 1 holds the rare "adapter"; chunk 2 only the common "lora"."""
    index = build_index(DOCUMENTS)

    results = rank(index, ["lora", "adapter"], 5)

    assert [chunk_id for chunk_id, _ in results] == [1, 2]


def test_a_shorter_chunk_outranks_a_longer_one() -> None:
    """Chunk 2 has "lora" once in 1 token; chunk 1 twice in 3 tokens.

    Length normalisation is what puts the short one first, even with a lower
    term frequency.
    """
    index = build_index(DOCUMENTS)

    results = rank(index, ["lora"], 5)

    assert [chunk_id for chunk_id, _ in results] == [2, 1]


def test_results_are_sorted_by_descending_score() -> None:
    """The best chunk comes first."""
    index = build_index(DOCUMENTS)

    scores = [score for _, score in rank(index, ["lora", "adapter"], 5)]

    assert scores == sorted(scores, reverse=True)


def test_ties_are_broken_by_chunk_id() -> None:
    """Equal scores are ordered by chunk id, not by insertion order."""
    index = build_index([(7, ["lora"]), (3, ["lora"])])

    results = rank(index, ["lora"], 5)

    assert [chunk_id for chunk_id, _ in results] == [3, 7]


@pytest.mark.parametrize("k, expected", [(1, 1), (2, 2), (5, 2), (0, 0)])
def test_at_most_k_results_are_returned(k: int, expected: int) -> None:
    """``k`` caps the results, and the corpus caps them too.

    Args:
        k: How many results are asked for.
        expected: How many come back.
    """
    index = build_index(DOCUMENTS)

    assert len(rank(index, ["lora"], k)) == expected


@pytest.mark.parametrize(
    "query_tokens",
    [[], ["kubernetes"], ["kubernetes", "terraform"]],
    ids=["empty", "one-unknown", "all-unknown"],
)
def test_a_query_without_known_terms_returns_nothing(
    query_tokens: list[str]
) -> None:
    """No known term means no candidate, not an error.

    Args:
        query_tokens: A query the corpus cannot match.
    """
    index = build_index(DOCUMENTS)

    assert rank(index, query_tokens, 5) == []
