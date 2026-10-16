"""Use case: answer every question of a search results file."""

from collections.abc import Callable
from pathlib import Path

from tqdm import tqdm

from src.adapters.json_results import (
    load_search_results,
    write_search_results
)
from src.application.answer import (
    NO_SOURCES_ANSWER,
    Generator,
    answer_from_sources
)
from src.domain.models import MinimalAnswer, StudentSearchResultsAndAnswer


def run_answer_dataset(
    student_search_results_path: str,
    save_directory: str,
    load_generator: Callable[[], Generator]
) -> Path:
    """Answer every question with the sources it already has, and save it.

    Sources are not searched again: the file from ``search_dataset`` already
    holds them. The model is loaded once, after the file is read, so a
    missing or broken file never pays for it, and then reused for every
    question.

    Args:
        student_search_results_path: Path of the ``search_dataset`` output.
        save_directory: Folder where the answers file is written.
        load_generator: Loads the model when it is called.

    Returns:
        Path of the written file, named like the input file.

    Raises:
        ValueError: If the input cannot be read, a source file cannot be
            read, or the output cannot be written.
    """
    results = load_search_results(Path(student_search_results_path))
    generator = load_generator()
    answers: list[MinimalAnswer] = []

    for result in tqdm(
        results.search_results,
        desc="Answering",
        unit="question"
    ):
        if result.retrieved_sources:
            answer = answer_from_sources(
                result.question, result.retrieved_sources, generator
            )
        else:
            answer = NO_SOURCES_ANSWER
        answers.append(
            MinimalAnswer(
                question_id=result.question_id,
                question=result.question,
                retrieved_sources=result.retrieved_sources,
                answer=answer
            )
        )

    output = StudentSearchResultsAndAnswer(
        search_results=answers,
        k=results.k
    )
    output_path = Path(save_directory) / Path(student_search_results_path).name
    write_search_results(output, output_path)
    return output_path
