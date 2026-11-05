"""The version of the code that shapes the index, for the caches to compare.

The incremental index and ``index.pkl`` are reused only while their key is
the same. Their inputs (the corpus text, the chunk size, the SQLite file) are
not enough: a new chunker or tokenizer must also invalidate them, otherwise
the caches keep serving what the old code produced.
"""

import hashlib
import inspect

from src.domain import bm25, chunking, tokenizer


# The modules whose code decides what the caches hold: how the corpus is cut
# (chunking), how a text becomes terms (tokenizer) and what is counted for
# BM25 (bm25). A tuple, so it cannot change while the program runs.
INDEXING_MODULES = (chunking, tokenizer, bm25)


def code_version() -> str:
    """Summarise the indexing code in 64 characters.

    The source is hashed instead of a version number kept by hand, because
    nobody has to remember to bump it. The cost: editing a comment also
    invalidates the caches, which only means one rebuild.

    Returns:
        The hexadecimal SHA-256 digest of the source of ``INDEXING_MODULES``.
    """
    digest = hashlib.sha256()
    for module in INDEXING_MODULES:
        digest.update(inspect.getsource(module).encode("utf-8"))
    return digest.hexdigest()
