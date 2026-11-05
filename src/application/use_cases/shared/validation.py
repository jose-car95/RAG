"""Argument checks shared by every search, answer and dataset use case.

One definition of each rule, so that no use case repeats it or depends on
another one to get it.
"""


def validate_k(k: int) -> None:
    """Reject a number of sources a search cannot work with.

    The one definition of the rule, so ``search_dataset`` (which has no
    query) and ``validate_query_and_k`` share it. ``bool`` is rejected on
    purpose: it is a subclass of ``int``, so ``True`` would pass as 1.

    Args:
        k: Number of sources asked for.

    Raises:
        ValueError: If ``k`` is not a positive integer.
    """
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k must be a positive integer")


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
    validate_k(k)
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query must not be empty")
    return clean_query
