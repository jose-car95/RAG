"""Turn text into the tokens the lexical retriever compares."""

import re


# A token is a run of lowercase letters, digits and underscores. Digits and
# underscores stay inside it because they carry meaning in this corpus:
# ``int8`` is the name of a technique, and 79 of the 199 reference questions
# ask about identifiers such as ``lm_eval`` or ``_call_hf_processor``, whose
# rarity is what makes them useful to BM25. ``tokenize`` adds their parts on
# top, so a question that paraphrases an identifier can match it too.
WORD_PATTERN = re.compile(r"[a-z0-9_]+")


def _identifier_parts(word: str) -> list[str]:
    """Split an identifier into the words joined by its underscores.

    A word without an underscore has no parts: returning it again would
    count every ordinary word twice. Empty pieces, which leading, trailing
    or doubled underscores leave behind, are dropped.

    Args:
        word: A single token, already lowercase.

    Returns:
        The non-empty parts in order, or an empty list.
    """
    if "_" in word:
        return [part for part in word.split("_") if part]
    return []


def tokenize(text: str) -> list[str]:
    """Split a text into its comparable tokens.

    The same rules are applied to the query and to the corpus, otherwise the
    two sides would never match. Repetitions are kept, in order, because BM25
    scores a chunk by how many times each term appears in it. An identifier
    with underscores is kept whole and followed by its parts (``lm_eval``
    gives ``lm_eval``, ``lm``, ``eval``): a question may quote it verbatim or
    paraphrase it (subject VI.1).

    Args:
        text: Any text, in any case, possibly empty.

    Returns:
        The lowercase tokens in order of appearance, empty if the text holds
        no letter, digit or underscore.
    """
    tokens: list[str] = []
    for word in WORD_PATTERN.findall(text.lower()):
        tokens.append(word)
        tokens.extend(_identifier_parts(word))

    return tokens
