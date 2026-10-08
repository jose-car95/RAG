"""Tests for the recall@k rules of the domain."""

import pytest

from src.domain.models import MinimalSource
from src.domain.recall import iou, is_match, recall_at_k

FILE = "data/raw/vllm-0.10.1/vllm/model_executor/layers/fused_moe/a.py"
OTHER_FILE = "data/raw/vllm-0.10.1/docs/features/lora.md"

# A real reference source of the public code dataset, 559 characters wide.
CORRECT = MinimalSource(
    file_path=FILE,
    first_character_index=28416,
    last_character_index=28975,
)


def source(first: int, last: int, file_path: str = FILE) -> MinimalSource:
    """Build a source in ``file_path`` covering ``[first, last)``.

    Args:
        first: First character index.
        last: Last character index (exclusive).
        file_path: File the source belongs to.

    Returns:
        The source.
    """
    return MinimalSource(
        file_path=file_path,
        first_character_index=first,
        last_character_index=last,
    )


def test_identical_ranges_have_iou_one() -> None:
    """A range compared with itself overlaps completely."""
    assert iou(CORRECT, CORRECT) == 1.0


def test_disjoint_ranges_have_iou_zero() -> None:
    """Ranges that do not touch share nothing."""
    assert iou(source(0, 100), source(200, 300)) == 0.0


def test_adjacent_ranges_have_iou_zero() -> None:
    """``last`` is exclusive, so ``[0, 100)`` and ``[100, 200)`` never meet."""
    assert iou(source(0, 100), source(100, 200)) == 0.0


def test_partial_overlap_is_intersection_over_union() -> None:
    """``[0, 100)`` and ``[50, 150)`` share 50 of 150 characters."""
    assert iou(source(0, 100), source(50, 150)) == pytest.approx(1 / 3)


def test_two_empty_ranges_have_iou_zero() -> None:
    """Nothing overlaps with nothing; the reference tool divides by zero."""
    assert iou(source(5, 5), source(5, 5)) == 0.0


def test_iou_is_symmetric() -> None:
    """The order of the two ranges does not change the result."""
    first, second = source(0, 100), source(50, 150)

    assert iou(first, second) == iou(second, first)


def test_same_range_in_the_same_file_matches() -> None:
    """A result identical to the correct source is found."""
    assert is_match(CORRECT, CORRECT)


def test_same_range_in_another_file_never_matches() -> None:
    """``file_path`` must be exact: the range alone is not enough."""
    assert not is_match(CORRECT, source(28416, 28975, OTHER_FILE))


@pytest.mark.parametrize(
    ("first", "expected"),
    [
        (28946, True),   # shares 29 of 560 characters: IoU 0.0518
        (28947, False),  # shares 28 of 560 characters: IoU exactly 0.05
        (28948, False),  # shares 27 of 560 characters: IoU 0.0482
    ],
    ids=["just_above", "exactly_0.05", "just_below"],
)
def test_iou_must_be_strictly_above_the_threshold(
    first: int, expected: bool
) -> None:
    """Measured with the reference tool: exactly 0.05 does not count."""
    assert is_match(CORRECT, source(first, 28976)) is expected


def test_correct_source_at_position_four() -> None:
    """A hit at position 4 counts from k=5 on, never in k=1 or k=3."""
    retrieved = [source(0, 10), source(20, 30), source(40, 50), CORRECT]

    assert recall_at_k([CORRECT], retrieved, 1) == 0.0
    assert recall_at_k([CORRECT], retrieved, 3) == 0.0
    assert recall_at_k([CORRECT], retrieved, 5) == 1.0
    assert recall_at_k([CORRECT], retrieved, 10) == 1.0


def test_recall_is_the_share_of_correct_sources_found() -> None:
    """Finding one of two correct sources is a recall of 0.5."""
    other_correct = source(0, 500)

    assert recall_at_k([CORRECT, other_correct], [CORRECT], 5) == 0.5


def test_nothing_retrieved_is_a_recall_of_zero() -> None:
    """An empty result list finds nothing."""
    assert recall_at_k([CORRECT], [], 5) == 0.0


def test_one_result_covering_two_sources_finds_both() -> None:
    """Each correct source is checked on its own against the top k."""
    left, right = source(0, 100), source(100, 200)

    assert recall_at_k([left, right], [source(0, 200)], 1) == 1.0
