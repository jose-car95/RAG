"""Use case: search every question of a dataset and save the results."""

from pathlib import Path
from tqdm import tqdm

from src.adapters.json_dataset import load_dataset
from src.adapters.json_results import write_search_results
from src.domain.models import (
    RagDataset,
    MinimalSearchResults,
    StudentSearchResults
)
from src.application.retrieval import load_index, search_index


def run_search_dataset(
    dataset_path: str,
    k: int,
    save_directory: str,
    index_path: str
) -> Path:
    """Search every question of a dataset and write the results.

    The index is loaded once, before the loop, and reused for every
    question: rebuilding it per question would need 184 s for 200
    questions, against the 90 s the subject allows.

    ``k`` is checked here as well as inside the search, on purpose: each use
    case validates its own input, and checking before loading the dataset
    avoids pointless work.

    Args:
        dataset_path: Path of the JSON dataset of questions.
        k: Number of sources requested per question; must be at least 1.
        save_directory: Folder where the results file is written.
        index_path: Path of the SQLite index built by ``index``.

    Returns:
        Path of the written file, named like the input dataset.

    Raises:
        ValueError: If ``k`` is not a positive integer, or the dataset or the
            index cannot be read, or the results cannot be written.
    """
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k must be a positive integer")

    dataset: RagDataset = load_dataset(Path(dataset_path))
    corpus = load_index(index_path)
    search_results: list[MinimalSearchResults] = []

    for question in tqdm(
        dataset.rag_questions,
        desc="Searching",
        unit="question"
    ):
        search_results.append(
            MinimalSearchResults(
                question_id=question.question_id,
                question=question.question,
                retrieved_sources=[
                    source for source, _ in search_index(
                        corpus,
                        question.question,
                        k
                    )
                ]
            )
        )

    results = StudentSearchResults(
        search_results=search_results,
        k=k
    )
    output_path = Path(save_directory) / Path(dataset_path).name
    write_search_results(results, output_path)
    return output_path
