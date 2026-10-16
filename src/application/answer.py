"""Use case: answer one question with the sources found for it."""

from collections.abc import Callable
from typing import Protocol

from src.adapters.corpus import read_source_text
from src.application.retrieval import (
    load_index,
    search_index,
    validate_query_and_k
)
from src.domain.models import MinimalSource
from src.domain.prompt import build_prompt

# About the top 5 sources fit, the same top 5 that Recall@5 measures; about
# 15 s per answer on CPU (measured in #55).
PROMPT_BUDGET: int = 2000
NO_SOURCES_ANSWER: str = (
    "No sources found, so the question cannot be answered."
)


class Generator(Protocol):
    """What the use case needs from a model: count tokens and answer.

    A port with two real reasons: Qwen in production and a fake in the
    tests, so no test has to load 1.5 GB of weights.
    """

    def count_tokens(self, text: str) -> int:
        """Count the tokens of a text.

        Args:
            text: Any text.

        Returns:
            The number of tokens.
        """
        ...

    def generate(self, prompt: str) -> str:
        """Answer a prompt.

        Args:
            prompt: The full prompt.

        Returns:
            The answer.
        """
        ...


def run_answer(
    query: str,
    k: int,
    index_path: str,
    load_generator: Callable[[], Generator]
) -> str:
    """Retrieve the sources of a question and let the model answer it.

    The model is passed as a loader, not loaded, so that this function
    decides when to pay for it: never for a rejected question or when no
    source is found.

    Args:
        query: Question to answer.
        k: Number of sources to retrieve.
        index_path: Path of the SQLite index.
        load_generator: Loads the model when it is called.

    Returns:
        The model's answer, or ``NO_SOURCES_ANSWER`` when nothing was found.

    Raises:
        ValueError: If the arguments are invalid, or the index or a source
            file cannot be read.
    """
    clean_query = validate_query_and_k(query, k)
    corpus = load_index(index_path)
    results = search_index(corpus, clean_query, k)
    if not results:
        return NO_SOURCES_ANSWER
    sources = [source for source, _ in results]
    return answer_from_sources(clean_query, sources, load_generator())


def answer_from_sources(
    question: str,
    sources: list[MinimalSource],
    generator: Generator
) -> str:
    """Answer a question from sources already retrieved.

    Takes the model already loaded, so a whole dataset loads it once and
    reuses it for every question.

    Args:
        question: The question, already validated.
        sources: Where to read the context, best first.
        generator: A loaded model.

    Returns:
        The model's answer.

    Raises:
        ValueError: If a source file cannot be read.
    """
    texts = [
        (source.file_path, read_source_text(source))
        for source in sources
    ]
    prompt = build_prompt(
        question, texts, generator.count_tokens, PROMPT_BUDGET
    )
    return generator.generate(prompt)
