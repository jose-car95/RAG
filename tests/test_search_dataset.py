"""Tests for the ``search_dataset`` use case."""

import json
import re
from pathlib import Path
from typing import cast

import pytest

from src.application import search_dataset as module
from src.application.index_corpus import run_index
from src.application.search_dataset import run_search_dataset

PUBLIC_DATASET = Path(
    "data/datasets/UnansweredQuestions/dataset_docs_public.json"
)
CORPUS_FILE = (
    "# Endpoints\n"
    "The http endpoint loads a lora adapter dynamically.\n"
    "\n"
    "# Quantization\n"
    "Use int8 or fp8 to shrink a model.\n"
)
OWN_QUESTIONS = {
    "rag_questions": [
        {"question_id": "q1", "question": "How to load a lora adapter?"},
        {"question_id": "q2", "question": "Which quantization is available?"},
        {"question_id": "q3", "question": "kubernetes terraform helm"},
    ]
}


def make_index(tmp_path: Path) -> Path:
    """Build a tiny index and return its path.

    Args:
        tmp_path: Temporary folder provided by pytest.

    Returns:
        Path of the SQLite index.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "notes.md").write_text(CORPUS_FILE, encoding="utf-8")
    index_path = tmp_path / "processed" / "index.db"
    run_index(str(corpus), 2000, str(index_path))
    return index_path


def make_own_dataset(tmp_path: Path) -> Path:
    """Write a three-question dataset matching the tiny corpus.

    Args:
        tmp_path: Temporary folder provided by pytest.

    Returns:
        Path of the dataset file.
    """
    dataset_path = tmp_path / "own_dataset.json"
    dataset_path.write_text(json.dumps(OWN_QUESTIONS), encoding="utf-8")
    return dataset_path


def read_results(output_path: Path) -> dict[str, object]:
    """Read a written results file.

    Args:
        output_path: Path of the results file.

    Returns:
        The parsed JSON.
    """
    with open(output_path, encoding="utf-8") as file:
        return cast(dict[str, object], json.load(file))


def test_results_file_is_written_with_one_entry_per_question(
    tmp_path: Path,
) -> None:
    """The output keeps every question of the dataset, in order."""
    index_path = make_index(tmp_path)

    output_path = run_search_dataset(
        str(PUBLIC_DATASET), 10, str(tmp_path), str(index_path)
    )

    assert output_path == tmp_path / "dataset_docs_public.json"
    written = read_results(output_path)
    with open(PUBLIC_DATASET, encoding="utf-8") as file:
        questions = json.load(file)["rag_questions"]

    entries = cast(list[dict[str, object]], written["search_results"])
    assert written["k"] == 10
    assert [entry["question_id"] for entry in entries] == [
        question["question_id"] for question in questions
    ]
    assert [entry["question"] for entry in entries] == [
        question["question"] for question in questions
    ]


def test_sources_come_from_the_index(tmp_path: Path) -> None:
    """Every question that matches the corpus gets its sources."""
    index_path = make_index(tmp_path)
    dataset_path = make_own_dataset(tmp_path)

    output_path = run_search_dataset(
        str(dataset_path), 5, str(tmp_path / "out"), str(index_path)
    )

    entries = cast(
        list[dict[str, object]], read_results(output_path)["search_results"]
    )
    by_id = {
        entry["question_id"]: entry["retrieved_sources"]
        for entry in entries
    }
    assert by_id["q1"], "the corpus talks about loading a lora adapter"
    assert by_id["q2"], "the corpus talks about quantization"
    assert by_id["q3"] == [], "no term of that question is in the corpus"


def test_every_source_respects_the_subject_limits(tmp_path: Path) -> None:
    """At most ``k`` sources per question, none wider than 2000 characters."""
    index_path = make_index(tmp_path)
    dataset_path = make_own_dataset(tmp_path)

    output_path = run_search_dataset(
        str(dataset_path), 2, str(tmp_path / "out"), str(index_path)
    )

    entries = cast(
        list[dict[str, object]], read_results(output_path)["search_results"]
    )
    for entry in entries:
        sources = cast(list[dict[str, int | str]], entry["retrieved_sources"])
        assert len(sources) <= 2
        for source in sources:
            width = (
                cast(int, source["last_character_index"])
                - cast(int, source["first_character_index"])
            )
            assert 0 < width <= 2000
            assert cast(str, source["file_path"]).endswith("notes.md")


def test_the_index_is_built_only_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rebuilding the index per question would blow the 90 s budget.

    Args:
        tmp_path: Temporary folder provided by pytest.
        monkeypatch: Fixture used to count the calls.
    """
    index_path = make_index(tmp_path)
    dataset_path = make_own_dataset(tmp_path)
    calls = []
    original = module.load_index

    def counted(path: str) -> object:
        calls.append(path)
        return original(path)

    monkeypatch.setattr(module, "load_index", counted)

    run_search_dataset(
        str(dataset_path), 5, str(tmp_path / "out"), str(index_path)
    )

    assert len(calls) == 1


def test_missing_save_directories_are_created(tmp_path: Path) -> None:
    """Nested output folders that do not exist yet are created."""
    index_path = make_index(tmp_path)
    save_directory = tmp_path / "new" / "nested"

    output_path = run_search_dataset(
        str(PUBLIC_DATASET), 5, str(save_directory), str(index_path)
    )

    assert output_path.is_file()


@pytest.mark.parametrize(
    "k",
    [0, -3, "abc", True],
    ids=["zero", "negative", "text", "bool"],
)
def test_invalid_k_is_rejected_before_writing(
    tmp_path: Path, k: object
) -> None:
    """``k`` must be a positive integer, and nothing is written otherwise."""
    index_path = make_index(tmp_path)
    save_directory = tmp_path / "results"

    with pytest.raises(ValueError, match="^k must be a positive integer$"):
        # Fire can pass text (e.g. "abc"); the type checker cannot see that.
        run_search_dataset(
            str(PUBLIC_DATASET),
            cast(int, k),
            str(save_directory),
            str(index_path),
        )

    assert not save_directory.exists()


def test_a_missing_index_is_reported(tmp_path: Path) -> None:
    """Searching a dataset without an index says what to run."""
    index_path = tmp_path / "processed" / "index.db"
    save_directory = tmp_path / "results"
    message = f"^index not found: {index_path}; run index first$"

    with pytest.raises(ValueError, match=message):
        run_search_dataset(
            str(PUBLIC_DATASET), 10, str(save_directory), str(index_path)
        )

    assert not index_path.exists()


def test_unwritable_save_directory_is_reported(tmp_path: Path) -> None:
    """A save directory that is really a file ends in a clear error."""
    index_path = make_index(tmp_path)
    not_a_directory = tmp_path / "a_file.txt"
    not_a_directory.write_text("not a folder", encoding="utf-8")
    output_path = not_a_directory / "dataset_docs_public.json"

    with pytest.raises(
        ValueError,
        match=f"^{re.escape(f'cannot write search results: {output_path}')}$",
    ):
        run_search_dataset(
            str(PUBLIC_DATASET), 10, str(not_a_directory), str(index_path)
        )


def test_missing_dataset_is_still_reported(tmp_path: Path) -> None:
    """Errors from loading the dataset reach the caller unchanged."""
    index_path = make_index(tmp_path)

    with pytest.raises(ValueError, match="^dataset not found: "):
        run_search_dataset(
            "/nonexistent/dataset.json", 10, str(tmp_path), str(index_path)
        )
