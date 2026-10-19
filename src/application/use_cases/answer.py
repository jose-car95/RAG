"""Use case: answer one question with the sources found for it."""

from src.application.ports.corpus_reader import CorpusReader
from src.application.ports.generator import Generator, GeneratorLoader
from src.application.ports.index_store import IndexStore
from src.application.use_cases.retrieval import (
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


def run_answer(
    query: str,
    k: int,
    index_path: str,
    index_store: IndexStore,
    corpus: CorpusReader,
    load_generator: GeneratorLoader
) -> str:
    """Retrieve the sources of a question and let the model answer it.

    The model is passed as a loader, not loaded, so that this function
    decides when to pay for it: never for a rejected question or when no
    source is found.

    Args:
        query: Question to answer.
        k: Number of sources to retrieve.
        index_path: Where the index lives.
        index_store: Reads the stored chunks.
        corpus: Reads the text of each source.
        load_generator: Loads the model when it is called.

    Returns:
        The model's answer, or ``NO_SOURCES_ANSWER`` when nothing was found.

    Raises:
        ValueError: If the arguments are invalid, or the index or a source
            file cannot be read.
    """
    clean_query = validate_query_and_k(query, k)
    index = load_index(index_path, index_store)
    results = search_index(index, clean_query, k)
    if not results:
        return NO_SOURCES_ANSWER
    sources = [source for source, _ in results]
    return answer_from_sources(
        clean_query, sources, corpus, load_generator()
    )


def answer_from_sources(
    question: str,
    sources: list[MinimalSource],
    corpus: CorpusReader,
    generator: Generator
) -> str:
    """Answer a question from sources already retrieved.

    Takes the model already loaded, so a whole dataset loads it once and
    reuses it for every question.

    Args:
        question: The question, already validated.
        sources: Where to read the context, best first.
        corpus: Reads the text of each source.
        generator: A loaded model.

    Returns:
        The model's answer.

    Raises:
        ValueError: If a source file cannot be read.
    """
    texts = [
        (source.file_path, corpus.read_source(source))
        for source in sources
    ]
    prompt = build_prompt(
        question, texts, generator.count_tokens, PROMPT_BUDGET
    )
    return generator.generate(prompt)
