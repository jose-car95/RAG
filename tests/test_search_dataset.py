"""Tests for the ``search_dataset`` use case."""

import json
import re
from pathlib import Path
from typing import cast

import pytest

from src.application.search_dataset import run_search_dataset

PUBLIC_DATASET = Path(
    "data/datasets/UnansweredQuestions/dataset_docs_public.json"
)


def test_results_file_is_written_with_one_entry_per_question(
    tmp_path: Path,
) -> None:
    """The output keeps every question, in order, with empty sources."""
    output_path = run_search_dataset(str(PUBLIC_DATASET), 10, str(tmp_path))

    assert output_path == tmp_path / "dataset_docs_public.json"
    with open(output_path, encoding="utf-8") as file:
        written = json.load(file)
    with open(PUBLIC_DATASET, encoding="utf-8") as file:
        questions = json.load(file)["rag_questions"]

    assert written["k"] == 10
    assert [entry["question_id"] for entry in written["search_results"]] == [
        question["question_id"] for question in questions
    ]
    assert [entry["question"] for entry in written["search_results"]] == [
        question["question"] for question in questions
    ]
    assert all(
        entry["retrieved_sources"] == []
        for entry in written["search_results"]
    )


def test_missing_save_directories_are_created(tmp_path: Path) -> None:
    """Nested output folders that do not exist yet are created."""
    save_directory = tmp_path / "new" / "nested"

    output_path = run_search_dataset(
        str(PUBLIC_DATASET), 5, str(save_directory)
    )

    assert output_path.is_file()


@pytest.mark.parametrize("k", [0, -3, "abc"], ids=["zero", "negative", "text"])
def test_invalid_k_is_rejected_before_writing(
    tmp_path: Path, k: object
) -> None:
    """``k`` must be a positive integer, and nothing is written otherwise."""
    save_directory = tmp_path / "results"

    with pytest.raises(ValueError, match="^k must be a positive integer$"):
        # Fire can pass text (e.g. "abc"); the type checker cannot see that.
        run_search_dataset(
            str(PUBLIC_DATASET), cast(int, k), str(save_directory)
        )

    assert not save_directory.exists()


def test_unwritable_save_directory_is_reported(tmp_path: Path) -> None:
    """A save directory that is really a file ends in a clear error."""
    not_a_directory = tmp_path / "a_file.txt"
    not_a_directory.write_text("not a folder", encoding="utf-8")
    output_path = not_a_directory / "dataset_docs_public.json"

    with pytest.raises(
        ValueError,
        match=f"^{re.escape(f'cannot write search results: {output_path}')}$",
    ):
        run_search_dataset(str(PUBLIC_DATASET), 10, str(not_a_directory))


def test_missing_dataset_is_still_reported(tmp_path: Path) -> None:
    """Errors from loading the dataset reach the caller unchanged."""
    with pytest.raises(ValueError, match="^dataset not found: "):
        run_search_dataset("/nonexistent/dataset.json", 10, str(tmp_path))
