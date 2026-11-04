"""Turn text into the tokens the lexical retriever compares."""

import re


# A word is a run of letters, digits and underscores, read before lowering
# the text so that the capital letters inside it are still visible: they mark
# where ``MolmoForCausalLM`` joins its words. Digits and underscores stay in
# the word because they carry meaning here: ``int8`` is the name of a
# technique, and 79 of the 199 reference questions ask about identifiers such
# as ``lm_eval`` or ``_call_hf_processor``, whose rarity is what makes them
# useful to BM25. ``tokenize`` adds their parts on top, so a question that
# paraphrases an identifier can match it too.
WORD_PATTERN = re.compile(r"[A-Za-z0-9_]+")
# One CamelCase word: an acronym before a capitalized word (the ``HTTP`` in
# ``HTTPServer``), or a capitalized/lowercase run, or an all-caps run, each
# keeping the digits that trail it. Case transitions split; digits never do,
# so ``int8`` and ``FP8`` stay whole while ``DeepSeekV2`` gives ``v2``.
CAMEL_PATTERN = re.compile(
    r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+[0-9]*|[A-Z]+[0-9]*|[0-9]+"
)


def _identifier_parts(word: str) -> list[str]:
    """Split an identifier into its underscore and CamelCase words.

    Each underscore piece is split again at its capital-letter boundaries,
    and every part is lowered. Empty pieces, left by leading, trailing or
    doubled underscores, are dropped.

    Args:
        word: A single word, in its original case.

    Returns:
        The non-empty parts in order; may be empty.
    """
    parts: list[str] = []
    for piece in word.split("_"):
        parts.extend(match.lower() for match in CAMEL_PATTERN.findall(piece))
    return parts


def tokenize(text: str) -> list[str]:
    """Split a text into its comparable tokens.

    The same rules are applied to the query and to the corpus, otherwise the
    two sides would never match. Repetitions are kept, in order, because BM25
    scores a chunk by how many times each term appears in it. An identifier
    is kept whole and followed by its parts, split at underscores and at
    CamelCase boundaries (``lm_eval`` gives ``lm_eval``, ``lm``, ``eval``;
    ``DeepSeek`` gives ``deepseek``, ``deep``, ``seek``): a question may quote
    it verbatim or paraphrase it (subject VI.1). A word with no inner part,
    such as a plain ``server``, is added only once.

    Args:
        text: Any text, in any case, possibly empty.

    Returns:
        The lowercase tokens in order of appearance, empty if the text holds
        no letter, digit or underscore.
    """
    tokens: list[str] = []
    for word in WORD_PATTERN.findall(text):
        lowered = word.lower()
        tokens.append(lowered)
        parts = _identifier_parts(word)
        if parts != [lowered]:
            tokens.extend(parts)

    return tokens
