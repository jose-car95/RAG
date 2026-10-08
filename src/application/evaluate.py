"""Use case: score saved search results against a reference dataset."""

from pathlib import Path

from src.adapters.json_dataset import load_dataset
from src.adapters.json_results import load_search_results
from src.domain.models import (
    AnsweredQuestion,
    RagDataset,
    StudentSearchResults
)
from src.domain.recall import RECALL_KS, recall_at_k


def run_evaluate(
    student_search_results_path: str,
    dataset_path: str
) -> dict[int, float]:
    """Compute recall@k of search results for every k in ``RECALL_KS``.

    The mean is taken over the questions of the reference dataset, not over
    the results: a question missing from the results counts as 0, as the
    reference tool does. Questions are matched by ``question_id``.

    Args:
        student_search_results_path: Path of the file written by
            ``search_dataset``.
        dataset_path: Path of a dataset whose questions carry their correct
            sources (``AnsweredQuestions``).

    Returns:
        Each k mapped to its recall, from 0.0 to 1.0.

    Raises:
        ValueError: If a file cannot be read, the dataset has no questions,
            or a question has no reference sources (dividing by zero would
            be the alternative).
    """
    dataset: RagDataset = load_dataset(Path(dataset_path))
    results: StudentSearchResults = load_search_results(
        Path(student_search_results_path)
    )

    if not dataset.rag_questions:
        raise ValueError(f"dataset has no questions: {dataset_path}")

    answered_questions: list[AnsweredQuestion] = []
    for question in dataset.rag_questions:
        if not isinstance(question, AnsweredQuestion) or not question.sources:
            raise ValueError(
                f"dataset has no reference sources: {dataset_path}"
            )
        answered_questions.append(question)

    retrieved_by_id = {
        result.question_id: result.retrieved_sources
        for result in results.search_results
    }

    recalls: dict[int, float] = {}

    for k in RECALL_KS:
        total = 0.0
        for question in answered_questions:
            retrieved = retrieved_by_id.get(question.question_id, [])
            total += recall_at_k(question.sources, retrieved, k)
        recalls[k] = total / len(answered_questions)
    return recalls
