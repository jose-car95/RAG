"""Use case: answer every question of a search results file."""

from pathlib import Path
from typing import NamedTuple

from tqdm import tqdm

from src.application.ports.corpus_reader import CorpusReader
from src.application.ports.dataset_store import DatasetStore
from src.application.ports.generator import GeneratorLoader
from src.application.use_cases.answer import (
    NO_SOURCES_ANSWER,
    answer_from_sources
)
from src.domain.models import MinimalAnswer, StudentSearchResultsAndAnswer


class AnswerDatasetResult(NamedTuple):
    """What the CLI needs to report a finished run.

    Attributes:
        output_path: The file written, named like the input file.
        question_count: Questions loaded, and answered: any failure stops
            the run before a result exists.
    """

    output_path: Path
    question_count: int


def run_answer_dataset(
    student_search_results_path: str,
    save_directory: str,
    datasets: DatasetStore,
    corpus: CorpusReader,
    load_generator: GeneratorLoader
) -> AnswerDatasetResult:
    """Answer every question with the sources it already has, and save it.

    Sources are not searched again: the file from ``search_dataset`` already
    holds them. The model is loaded once, after the file is read, so a
    missing or broken file never pays for it, and then reused for every
    question.

    Args:
        student_search_results_path: Path of the ``search_dataset`` output.
        save_directory: Folder where the answers file is written.
        datasets: Reads the search results and writes the answers.
        corpus: Reads the text of each source.
        load_generator: Loads the model when it is called.

    Returns:
        The path of the written file and how many questions it holds.

    Raises:
        ValueError: If the input cannot be read, a source file cannot be
            read, or the output cannot be written.
    """
    results = datasets.load_search_results(
        Path(student_search_results_path)
    )
    generator = load_generator()
    answers: list[MinimalAnswer] = []

    for result in tqdm(
        results.search_results,
        desc="Answering",
        unit="question"
    ):
        if result.retrieved_sources:
            answer = answer_from_sources(
                result.question,
                result.retrieved_sources,
                corpus,
                generator
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
    datasets.write_results(output, output_path)

    return AnswerDatasetResult(
        output_path=output_path,
        question_count=len(answers)
    )
