"""Use case: search every question of a dataset and save the results."""

from pathlib import Path

from src.adapters.json_dataset import load_dataset
from src.adapters.json_results import write_search_results
from src.domain.models import (
    RagDataset,
    MinimalSearchResults,
    StudentSearchResults
)


def run_search_dataset(dataset_path: str, k: int, save_directory: str) -> Path:
    """Search a whole dataset and write a ``StudentSearchResults`` file.

    Retrieval does not exist yet, so every question gets empty sources.

    Args:
        dataset_path: Path of the JSON dataset of questions.
        k: Number of sources requested per question; must be at least 1.
        save_directory: Folder where the results file is written.

    Returns:
        Path of the written file, named like the input dataset.

    Raises:
        ValueError: If ``k`` is not a positive integer, or the dataset
            cannot be loaded, or the results cannot be written.
    """
    if not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer")

    dataset: RagDataset = load_dataset(Path(dataset_path))

    search_results: list[MinimalSearchResults] = []
    for question in dataset.rag_questions:
        search_results.append(
            MinimalSearchResults(
                question_id=question.question_id,
                question=question.question,
                retrieved_sources=[]
            )
        )

    results = StudentSearchResults(
        search_results=search_results,
        k=k
    )
    output_path = Path(save_directory) / Path(dataset_path).name
    write_search_results(results, output_path)
    return output_path
