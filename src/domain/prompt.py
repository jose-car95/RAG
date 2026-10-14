"""Build the prompt that hands the retrieved sources to the model."""

from collections.abc import Callable


# Short imperative sentences work best with a small model. The exact refusal
# sentence gives it a ready answer when the sources do not hold one, instead of
# inventing; "short" also saves generation time on CPU.
INSTRUCTION: str = (
    "Answer the question using only the sources below. "
    "If the sources do not contain the answer, "
    "say that you cannot answer from the available sources. "
    "Keep the answer short."
)


def build_prompt(
    question: str,
    sources: list[tuple[str, str]],
    count_tokens: Callable[[str], int],
    budget: int
) -> str:
    """Write the instruction, the sources that fit and the question.

    Sources are added best first, as numbered sections with their file path,
    until the next one would push the whole prompt over ``budget``; from there
    none is added, not even a smaller one (decision A). The question goes last,
    because it is what the model continues from.

    Args:
        question: The user's question.
        sources: ``(file_path, text)`` pairs, best first.
        count_tokens: Counts the tokens of a text; the real tokenizer in
            production, a simple stand-in in the tests.
        budget: Maximum number of tokens of the whole prompt.

    Returns:
        The prompt text; without sources when not even the first one fits.
    """
    parts = [INSTRUCTION]
    closing = f"Question: {question}"
    for number, (file_path, text) in enumerate(sources, start=1):
        section = f"[{number}] {file_path}\n{text}"
        candidate = "\n\n".join(parts + [section, closing])
        if count_tokens(candidate) > budget:
            break
        parts.append(section)
    return "\n\n".join(parts + [closing])
