"""Tests for answering a whole file of search results.

The model is the same fake as in ``test_answer.py``: it records every prompt
and counts how often it is loaded, so no test needs the Qwen weights.
"""

import json
from pathlib import Path

import pytest

from src.application.answer import NO_SOURCES_ANSWER
from src.application.answer_dataset import run_answer_dataset
from src.domain.models import StudentSearchResultsAndAnswer
from tests.test_answer import MD_FILE, FakeLoader


def write_results(tmp_path: Path) -> Path:
    """Write a corpus file and three search results pointing at it.

    The first two questions have a source; the third found none.

    Args:
        tmp_path: Temporary folder provided by pytest.

    Returns:
        Path of the search results file.
    """
    corpus_file = tmp_path / "lora.md"
    corpus_file.write_text(MD_FILE, encoding="utf-8")
    source = {
        "file_path": str(corpus_file),
        "first_character_index": 12,
        "last_character_index": 51,
    }
    results = {
        "search_results": [
            {
                "question_id": "q1",
                "question": "How do I load a lora adapter?",
                "retrieved_sources": [source],
            },
            {
                "question_id": "q2",
                "question": "What does the http endpoint load?",
                "retrieved_sources": [source],
            },
            {
                "question_id": "q3",
                "question": "asdfghjkl",
                "retrieved_sources": [],
            },
        ],
        "k": 5,
    }
    path = tmp_path / "search" / "dataset_docs_public.json"
    path.parent.mkdir()
    path.write_text(json.dumps(results), encoding="utf-8")
    return path


def test_every_question_gets_an_answer(tmp_path: Path) -> None:
    """Same questions, sources and k as the input, plus an answer each."""
    input_path = write_results(tmp_path)
    save_directory = tmp_path / "answers"
    loader = FakeLoader()

    output_path = run_answer_dataset(
        str(input_path), str(save_directory), loader
    )

    assert output_path == save_directory / "dataset_docs_public.json"
    written = StudentSearchResultsAndAnswer.model_validate_json(
        output_path.read_text(encoding="utf-8")
    )
    assert written.k == 5
    assert [entry.question_id for entry in written.search_results] == [
        "q1", "q2", "q3"
    ]
    assert written.search_results[0].question == (
        "How do I load a lora adapter?"
    )
    assert len(written.search_results[0].retrieved_sources) == 1
    assert written.search_results[0].answer == (
        "Use the load_lora_adapter endpoint."
    )


def test_model_is_loaded_once_for_the_whole_file(tmp_path: Path) -> None:
    """One load, one prompt per question that has sources."""
    loader = FakeLoader()

    run_answer_dataset(
        str(write_results(tmp_path)), str(tmp_path / "answers"), loader
    )

    assert loader.loads == 1
    assert len(loader.generator.prompts) == 2


def test_question_without_sources_is_not_sent_to_the_model(
    tmp_path: Path
) -> None:
    """Nothing to ground an answer on: the fixed message, no prompt."""
    loader = FakeLoader()

    output_path = run_answer_dataset(
        str(write_results(tmp_path)), str(tmp_path / "answers"), loader
    )

    written = StudentSearchResultsAndAnswer.model_validate_json(
        output_path.read_text(encoding="utf-8")
    )
    assert written.search_results[2].answer == NO_SOURCES_ANSWER
    assert all("asdfghjkl" not in p for p in loader.generator.prompts)


def test_missing_file_is_reported_without_the_model(tmp_path: Path) -> None:
    """A clear error, and Qwen never loaded."""
    loader = FakeLoader()

    with pytest.raises(ValueError, match="search results not found"):
        run_answer_dataset(
            str(tmp_path / "missing.json"), str(tmp_path / "answers"), loader
        )
    assert loader.loads == 0


def test_malformed_file_is_reported_without_the_model(tmp_path: Path) -> None:
    """Broken JSON is rejected before loading anything."""
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    loader = FakeLoader()

    with pytest.raises(ValueError, match="broken.json"):
        run_answer_dataset(str(broken), str(tmp_path / "answers"), loader)
    assert loader.loads == 0
