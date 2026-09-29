"""Turn text into the tokens the lexical retriever compares."""

import re


# A token is a run of lowercase letters, digits and underscores. Digits and
# underscores stay inside it because they carry meaning in this corpus:
# ``int8`` is the name of a technique, and 79 of the 199 reference questions
# ask about identifiers such as ``lm_eval`` or ``_call_hf_processor``, whose
# rarity is what makes them useful to BM25.
WORD_PATTERN = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    """Split a text into its comparable tokens.

    The same rules are applied to the query and to the corpus, otherwise the
    two sides would never match. Repetitions are kept, in order, because BM25
    scores a chunk by how many times each term appears in it.

    Args:
        text: Any text, in any case, possibly empty.

    Returns:
        The lowercase tokens in order of appearance, empty if the text holds
        no letter, digit or underscore.
    """
    return WORD_PATTERN.findall(text.lower())
