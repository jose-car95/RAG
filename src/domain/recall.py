"""Decide whether a retrieved source counts as found, and score recall@k.

The rules follow the subject (VII.1): a correct source is found when a
result in the top k is in the same file and overlaps its character range
with an IoU above ``IOU_THRESHOLD``.
"""

from src.domain.models import MinimalSource


# Strictly greater: measured with the reference tool, an IoU of exactly
# 0.05 does not count.
IOU_THRESHOLD = 0.05
# The values of k the subject reports.
RECALL_KS = (1, 3, 5, 10)


def iou(first: MinimalSource, second: MinimalSource) -> float:
    """Measure how much two character ranges overlap, from 0.0 to 1.0.

    IoU is the number of shared characters divided by the number of
    characters the two ranges cover together. ``last_character_index`` is
    exclusive, so ranges that only touch share nothing. The files are not
    compared here; that is the job of ``is_match``.

    Two empty ranges give 0.0 instead of dividing by zero: there are no
    characters, so nothing overlaps (decision A, ``docs/SPEC_NOTES.md``).

    Args:
        first: One range.
        second: The other range; the order does not change the result.

    Returns:
        1.0 for identical ranges, 0.0 for ranges that share nothing.
    """
    overlap_start = max(
        first.first_character_index, second.first_character_index
    )
    overlap_end = min(
        first.last_character_index, second.last_character_index
    )
    intersection = max(0, overlap_end - overlap_start)
    first_width = first.last_character_index - first.first_character_index
    second_width = second.last_character_index - second.first_character_index
    union = first_width + second_width - intersection
    if union == 0:
        return 0.0
    return intersection / union


def is_match(correct: MinimalSource, candidate: MinimalSource) -> bool:
    """Tell whether a retrieved source counts as finding a correct one.

    Args:
        correct: Source where the answer really is.
        candidate: Source returned by the retriever.

    Returns:
        True when both are in the same file and their IoU is above
        ``IOU_THRESHOLD``.
    """
    return (
        correct.file_path == candidate.file_path
        and iou(correct, candidate) > IOU_THRESHOLD
    )


def recall_at_k(
    correct: list[MinimalSource],
    retrieved: list[MinimalSource],
    k: int
) -> float:
    """Compute the share of correct sources found in the first k results.

    Each correct source is checked on its own, so one wide result can find
    several of them.

    Args:
        correct: Correct sources of one question; must not be empty.
        retrieved: Retrieved sources, best first.
        k: How many of the first results are looked at.

    Returns:
        A value from 0.0 (none found) to 1.0 (all found).
    """
    top_k = retrieved[:k]
    found = 0
    for source in correct:
        if any(is_match(source, candidate) for candidate in top_k):
            found += 1
    return found / len(correct)
