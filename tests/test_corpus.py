"""Tests for discovering the indexable files of the corpus."""

import re
from pathlib import Path

import pytest

from src.adapters.corpus import find_corpus_files


def make_files(root: Path, *relative_paths: str) -> None:
    """Create empty files (and their folders) under ``root``.

    Args:
        root: Folder where the files are created.
        *relative_paths: Paths of the files, relative to ``root``.
    """
    for relative_path in relative_paths:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content", encoding="utf-8")


def test_only_python_markdown_and_text_files_are_found(tmp_path: Path) -> None:
    """``.py``, ``.md`` and ``.txt`` files are found, at any depth."""
    make_files(
        tmp_path,
        "vllm/engine.py",
        "vllm/docs/lora.md",
        "vllm/docs/deep/notes.txt",
        "vllm/config.json",
        "vllm/logo.png",
        "vllm/kernel.cu",
    )

    files = find_corpus_files(str(tmp_path))

    assert files == [
        tmp_path / "vllm/docs/deep/notes.txt",
        tmp_path / "vllm/docs/lora.md",
        tmp_path / "vllm/engine.py",
    ]


def test_files_are_returned_in_sorted_order(tmp_path: Path) -> None:
    """The order is stable, so two runs index the same thing."""
    make_files(tmp_path, "b.py", "a.md", "c/a.txt")

    assert find_corpus_files(str(tmp_path)) == sorted(
        find_corpus_files(str(tmp_path))
    )


def test_paths_keep_the_prefix_as_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A relative folder gives relative paths, as the grader expects."""
    monkeypatch.chdir(tmp_path)
    make_files(tmp_path, "data/raw/vllm-0.10.1/docs/features/lora.md")

    files = find_corpus_files("data/raw")

    assert [str(path) for path in files] == [
        "data/raw/vllm-0.10.1/docs/features/lora.md"
    ]


def test_missing_folder_is_reported(tmp_path: Path) -> None:
    """A folder that does not exist ends in a clear error."""
    missing = tmp_path / "missing"

    with pytest.raises(
        ValueError,
        match=f"^{re.escape(f'corpus folder not found: {missing}')}$",
    ):
        find_corpus_files(str(missing))


@pytest.mark.parametrize(
    "files", [(), ("config.json", "logo.png")], ids=["empty", "no_indexable"]
)
def test_folder_without_indexable_files_is_reported(
    tmp_path: Path, files: tuple[str, ...]
) -> None:
    """A folder with nothing to index ends in a clear error."""
    make_files(tmp_path, *files)

    with pytest.raises(
        ValueError,
        match=f"^{re.escape(f'no indexable files in {tmp_path}')}$",
    ):
        find_corpus_files(str(tmp_path))
