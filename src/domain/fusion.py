"""Fuse several ranked lists into one with Reciprocal Rank Fusion."""

from src.domain.models import MinimalSource


# The damping constant from Cormack, Clarke & Buttcher (2009), also used by
# Elasticsearch. It flattens the gap between ranks, so merely reaching the top
# of a list counts and a single top position cannot dominate. Not tuned
# against the datasets, the same stance as BM25's k1 and b.
RRF_C: float = 60.0


def _source_key(source: MinimalSource) -> tuple[str, int, int]:
    """Identify a source across lists: two retrievers may return the same one.

    ``MinimalSource`` is a pydantic model and is not hashable, so a chunk is
    keyed by its file and character range, which is what makes it the same
    source in both rankings.

    Args:
        source: The source to identify.

    Returns:
        The file path and character range, usable as a dict key.
    """
    return (
        source.file_path,
        source.first_character_index,
        source.last_character_index
    )


def reciprocal_rank_fusion(
    rankings: list[list[MinimalSource]], c: float = RRF_C
) -> list[tuple[MinimalSource, float]]:
    """Merge ranked lists by reciprocal rank, best first.

    Each source scores ``1 / (c + position)`` in every list where it appears,
    summed across lists, so a source high in both rankings beats one high in
    only one. Only the position counts, never the retrievers' own scores,
    which live on different scales.

    Args:
        rankings: Ranked lists of sources, each best first.
        c: Damping constant; 60 by convention.

    Returns:
        Pairs of source and fused score, highest first; ties broken by the
        source key so the order never depends on dict iteration.
    """
    scores: dict[tuple[str, int, int], float] = {}
    sources: dict[tuple[str, int, int], MinimalSource] = {}
    for ranking in rankings:
        for position, source in enumerate(ranking, start=1):
            key = _source_key(source)
            scores[key] = scores.get(key, 0.0) + 1.0 / (c + position)
            sources.setdefault(key, source)
    fused = [(sources[key], score) for key, score in scores.items()]
    fused.sort(key=lambda pair: (-pair[1], _source_key(pair[0])))
    return fused
