"""Tests for the semantic ranking: cosine similarity over unit vectors.

Every vector here is already unit length, as the embedder leaves them, so
the cosine of two vectors is just their dot product and each expected score
can be checked by hand.
"""

import numpy as np

from src.domain.models import MinimalSource
from src.domain.semantic import SemanticIndex, rank_semantic


def source(name: str) -> MinimalSource:
    """Build a throwaway source so a row can be told from the others.

    Args:
        name: File name that makes the source unique.

    Returns:
        A source with that file path and a zero range.
    """
    return MinimalSource(
        file_path=name, first_character_index=0, last_character_index=0
    )


# Three unit vectors in the plane: east, north, and north-east halfway
# between them. Against an east query, east scores 1, north 0 and the
# diagonal about 0.707 (the cosine of 45 degrees).
EAST = np.array([1.0, 0.0], dtype=np.float32)
NORTH = np.array([0.0, 1.0], dtype=np.float32)
DIAGONAL = np.array([0.7071, 0.7071], dtype=np.float32)

INDEX = SemanticIndex(
    matrix=np.stack([EAST, NORTH, DIAGONAL]),
    sources=[source("east.md"), source("north.md"), source("diagonal.md")],
)


def test_the_closest_vector_comes_first() -> None:
    """An east query ranks east over the diagonal over north."""
    results = rank_semantic(INDEX, EAST, 3)

    assert [source.file_path for source, _ in results] == [
        "east.md",
        "diagonal.md",
        "north.md",
    ]


def test_the_score_is_the_cosine_of_the_angle() -> None:
    """1 for the same direction, about 0.707 at 45 degrees, 0 at 90."""
    [(_, east), (_, diagonal), (_, north)] = rank_semantic(INDEX, EAST, 3)

    assert east == 1.0
    assert round(diagonal, 4) == 0.7071
    assert round(north, 4) == 0.0


def test_k_limits_how_many_sources_come_back() -> None:
    """Only the best k rows are returned, best first."""
    results = rank_semantic(INDEX, EAST, 1)

    assert [source.file_path for source, _ in results] == ["east.md"]


def test_an_empty_index_returns_nothing() -> None:
    """A query against no vectors is empty, not an error."""
    empty = SemanticIndex(
        matrix=np.empty((0, 2), dtype=np.float32), sources=[]
    )

    assert rank_semantic(empty, EAST, 3) == []
