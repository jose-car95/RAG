"""Tests for loading question datasets from JSON files."""

import re
from pathlib import Path

import pytest

from src.adapters.json_dataset import load_dataset

PUBLIC_DATASET = "data/datasets/UnansweredQuestions/dataset_docs_public.json"


def expect_error(
    path: Path | str, message: str
) -> pytest.ExceptionInfo[ValueError]:
    """Load ``path`` and check it fails with exactly ``message``.

    Args:
        path: Dataset path to load.
        message: Expected error message, without the ``ERROR:`` prefix.

    Returns:
        Information about the raised error, for further checks.
    """
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$") as info:
        load_dataset(str(path))
    return info


def test_valid_dataset_is_loaded() -> None:
    """A public dataset is read and validated as a ``RagDataset``."""
    dataset = load_dataset(PUBLIC_DATASET)

    assert len(dataset.rag_questions) == 100


def test_missing_file_is_reported(tmp_path: Path) -> None:
    """A path that does not exist is reported as not found."""
    missing = tmp_path / "missing.json"

    info = expect_error(missing, f"dataset not found: {missing}")

    # The original error is kept as the cause, for debugging.
    assert isinstance(info.value.__cause__, FileNotFoundError)


def test_unreadable_path_is_reported(tmp_path: Path) -> None:
    """A path that cannot be opened as a file is reported as unreadable."""
    directory = tmp_path / "a_directory.json"
    directory.mkdir()

    expect_error(directory, f"cannot read dataset: {directory}")


@pytest.mark.parametrize(
    "content",
    [b"", b'{"rag_questions": [', b"\xff\xfe\x00bad"],
    ids=["empty", "truncated", "binary"],
)
def test_invalid_json_is_reported(tmp_path: Path, content: bytes) -> None:
    """Content that is not JSON text is reported as invalid JSON."""
    path = tmp_path / "dataset.json"
    path.write_bytes(content)

    expect_error(path, f"dataset is not valid JSON: {path}")


@pytest.mark.parametrize(
    "content",
    ['{"foo": 1}', "[1, 2, 3]"],
    ids=["unknown_keys", "a_list"],
)
def test_wrong_shape_is_reported_in_one_line(
    tmp_path: Path, content: str
) -> None:
    """Valid JSON that is not a dataset gets a one-line message."""
    path = tmp_path / "dataset.json"
    path.write_text(content, encoding="utf-8")

    expect_error(path, f"dataset does not match the expected format: {path}")
