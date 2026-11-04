"""Tests for Reciprocal Rank Fusion."""

from src.domain.fusion import RRF_C, reciprocal_rank_fusion
from src.domain.models import MinimalSource


def _source(path: str) -> MinimalSource:
    """Build a throwaway source identified by its path."""
    return MinimalSource(
        file_path=path, first_character_index=0, last_character_index=1
    )


def test_a_source_in_both_lists_beats_one_in_a_single_list() -> None:
    both = _source("both.py")
    lexical_only = _source("lex.py")
    semantic_only = _source("sem.py")
    lexical = [both, lexical_only]
    semantic = [both, semantic_only]
    fused = reciprocal_rank_fusion([lexical, semantic])
    assert fused[0][0] == both
    assert fused[0][1] == 2.0 / (RRF_C + 1)


def test_score_sums_one_over_c_plus_rank_across_lists() -> None:
    a = _source("a.py")
    # 1st in the first list and 2nd in the second.
    fused = reciprocal_rank_fusion([[a], [_source("x.py"), a]])
    assert fused[0][0] == a
    assert fused[0][1] == 1.0 / (RRF_C + 1) + 1.0 / (RRF_C + 2)


def test_a_source_in_a_single_list_still_appears() -> None:
    a = _source("a.py")
    b = _source("b.py")
    fused = reciprocal_rank_fusion([[a], [b]])
    assert {source.file_path for source, _ in fused} == {"a.py", "b.py"}


def test_empty_rankings_give_an_empty_result() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


def test_ties_are_broken_by_source_so_the_order_is_stable() -> None:
    a = _source("a.py")
    b = _source("b.py")
    # Each is 1st in one list: equal score, tie broken by the source key.
    fused = reciprocal_rank_fusion([[b], [a]])
    assert [source.file_path for source, _ in fused] == ["a.py", "b.py"]
