"""Tests for the ``evaluate`` use case and for reading search results."""

import json
from pathlib import Path

import pytest

from src.adapters.outbound.json_files import JsonDatasetStore
from src.application.use_cases.evaluate import run_evaluate

DATASETS = JsonDatasetStore()
CORRECT = {
    "file_path": "data/raw/vllm-0.10.1/docs/features/lora.md",
    "first_character_index": 4695,
    "last_character_index": 6098,
}
WRONG = {
    "file_path": "data/raw/vllm-0.10.1/docs/features/lora.md",
    "first_character_index": 0,
    "last_character_index": 1000,
}
DATASET = {
    "rag_questions": [
        {
            "question_id": "q1",
            "question": "How to load a lora adapter?",
            "sources": [CORRECT],
            "answer": "With the endpoint.",
        },
        {
            "question_id": "q2",
            "question": "Which quantization is available?",
            "sources": [CORRECT],
            "answer": "int8 and fp8.",
        },
    ]
}


def write_json(path: Path, data: object) -> Path:
    """Write ``data`` as JSON to ``path``.

    Args:
        path: File to create.
        data: Data to serialize.

    Returns:
        The same ``path``, for convenience.
    """
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def results_for(*entries: tuple[str, list[dict[str, object]]]) -> dict[
    str, object
]:
    """Build a ``StudentSearchResults`` document.

    Args:
        *entries: Pairs of question id and retrieved sources.

    Returns:
        The JSON-ready search results.
    """
    return {
        "search_results": [
            {
                "question_id": question_id,
                "question": "unused by the evaluation",
                "retrieved_sources": sources,
            }
            for question_id, sources in entries
        ],
        "k": 10,
    }


def test_reports_recall_at_one_three_five_and_ten(tmp_path: Path) -> None:
    """The result maps each k to the mean recall over the questions."""
    dataset = write_json(tmp_path / "dataset.json", DATASET)
    results = write_json(
        tmp_path / "results.json",
        results_for(
            ("q1", [CORRECT]),
            ("q2", [WRONG, WRONG, WRONG, CORRECT]),
        ),
    )

    evaluation = run_evaluate(str(results), str(dataset), DATASETS)

    assert evaluation.recalls == {1: 0.5, 3: 0.5, 5: 1.0, 10: 1.0}


def test_reports_the_mean_reciprocal_rank(tmp_path: Path) -> None:
    """q1 is found at position 1 and q2 at 4: (1 + 0.25) / 2."""
    dataset = write_json(tmp_path / "dataset.json", DATASET)
    results = write_json(
        tmp_path / "results.json",
        results_for(
            ("q1", [CORRECT]),
            ("q2", [WRONG, WRONG, WRONG, CORRECT]),
        ),
    )

    evaluation = run_evaluate(str(results), str(dataset), DATASETS)

    assert evaluation.mrr == 0.625


def test_question_missing_from_results_counts_as_zero(tmp_path: Path) -> None:
    """The mean is over the dataset questions, as the reference tool does."""
    dataset = write_json(tmp_path / "dataset.json", DATASET)
    results = write_json(
        tmp_path / "results.json", results_for(("q1", [CORRECT]))
    )

    evaluation = run_evaluate(str(results), str(dataset), DATASETS)

    assert evaluation.recalls == {1: 0.5, 3: 0.5, 5: 0.5, 10: 0.5}
    assert evaluation.mrr == 0.5


def test_dataset_without_reference_sources_is_rejected(
    tmp_path: Path,
) -> None:
    """An ``UnansweredQuestions`` dataset cannot be evaluated against."""
    dataset = write_json(
        tmp_path / "dataset.json",
        {"rag_questions": [{"question_id": "q1", "question": "Why?"}]},
    )
    results = write_json(tmp_path / "results.json", results_for())

    with pytest.raises(ValueError) as error:
        run_evaluate(str(results), str(dataset), DATASETS)

    assert str(error.value) == f"dataset has no reference sources: {dataset}"


def test_question_with_an_empty_sources_list_is_rejected(
    tmp_path: Path,
) -> None:
    """With no correct source the share found would be 0 / 0."""
    question = dict(DATASET["rag_questions"][0], sources=[])
    dataset = write_json(
        tmp_path / "dataset.json", {"rag_questions": [question]}
    )
    results = write_json(tmp_path / "results.json", results_for())

    with pytest.raises(ValueError) as error:
        run_evaluate(str(results), str(dataset), DATASETS)

    assert str(error.value) == f"dataset has no reference sources: {dataset}"


def test_dataset_without_questions_is_rejected(tmp_path: Path) -> None:
    """A mean over zero questions would divide by zero."""
    dataset = write_json(tmp_path / "dataset.json", {"rag_questions": []})
    results = write_json(tmp_path / "results.json", results_for())

    with pytest.raises(ValueError) as error:
        run_evaluate(str(results), str(dataset), DATASETS)

    assert str(error.value) == f"dataset has no questions: {dataset}"


def test_valid_search_results_are_loaded(tmp_path: Path) -> None:
    """A well-formed file becomes a ``StudentSearchResults``."""
    path = write_json(
        tmp_path / "results.json", results_for(("q1", [CORRECT]))
    )

    results = DATASETS.load_search_results(path)

    assert results.k == 10
    assert results.search_results[0].question_id == "q1"
    assert results.search_results[0].retrieved_sources[0].file_path == (
        CORRECT["file_path"]
    )


def test_missing_search_results_are_reported(tmp_path: Path) -> None:
    """A missing file names the path, in one line."""
    missing = tmp_path / "nope.json"

    with pytest.raises(ValueError) as error:
        DATASETS.load_search_results(missing)

    assert str(error.value) == f"search results not found: {missing}"


@pytest.mark.parametrize(
    ("content", "detail"),
    [
        (b"", " (line 1, column 1: Expecting value)"),
        (
            b"{not json",
            " (line 1, column 2: Expecting property name enclosed in"
            " double quotes)",
        ),
        (b"\xff\xfe", ""),
    ],
    ids=["empty", "broken", "binary"],
)
def test_invalid_json_search_results_are_reported(
    tmp_path: Path, content: bytes, detail: str
) -> None:
    """Malformed JSON or bytes that are not text end in one line."""
    path = tmp_path / "results.json"
    path.write_bytes(content)

    with pytest.raises(ValueError) as error:
        DATASETS.load_search_results(path)

    assert str(error.value) == (
        f"search results are not valid JSON: {path}{detail}"
    )


def test_wrong_shape_search_results_are_reported(tmp_path: Path) -> None:
    """Valid JSON that is not a ``StudentSearchResults`` is rejected."""
    path = write_json(tmp_path / "results.json", {"rag_questions": []})

    with pytest.raises(ValueError) as error:
        DATASETS.load_search_results(path)

    assert str(error.value) == (
        f"search results do not match the expected format: {path}"
        " (search_results: Field required)"
    )
