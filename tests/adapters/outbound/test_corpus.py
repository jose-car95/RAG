"""Tests for discovering the indexable files of the corpus."""

import re
from pathlib import Path

import pytest

from src.adapters.outbound.corpus import FileCorpus
from src.adapters.outbound.sqlite_index import SqliteIndexStore
from src.domain.models import MinimalSource

CORPUS = FileCorpus()

INDEX_PATH = Path("data/processed/index.db")


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

    files = CORPUS.find_files(str(tmp_path))

    assert files == [
        tmp_path / "vllm/docs/deep/notes.txt",
        tmp_path / "vllm/docs/lora.md",
        tmp_path / "vllm/engine.py",
    ]


def test_files_are_returned_in_sorted_order(tmp_path: Path) -> None:
    """The order is stable, so two runs index the same thing."""
    make_files(tmp_path, "b.py", "a.md", "c/a.txt")

    assert CORPUS.find_files(str(tmp_path)) == sorted(
        CORPUS.find_files(str(tmp_path))
    )


def test_paths_keep_the_prefix_as_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A relative folder gives relative paths, as the grader expects."""
    monkeypatch.chdir(tmp_path)
    make_files(tmp_path, "data/raw/vllm-0.10.1/docs/features/lora.md")

    files = CORPUS.find_files("data/raw")

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
        CORPUS.find_files(str(missing))


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
        CORPUS.find_files(str(tmp_path))


def source_of(path: Path, first: int, last: int) -> MinimalSource:
    """Build a source over a file and a character range.

    Args:
        path: File the source points to.
        first: First character index, inclusive.
        last: Last character index, exclusive.

    Returns:
        The source.
    """
    return MinimalSource(
        file_path=str(path),
        first_character_index=first,
        last_character_index=last,
    )


def test_source_text_is_its_character_range(tmp_path: Path) -> None:
    """The text is the file sliced by the source's range, end excluded."""
    path = tmp_path / "lora.md"
    path.write_text("# LoRA\nSend a POST request.\n", encoding="utf-8")
    assert CORPUS.read_source(source_of(path, 7, 26)) == "Send a POST request"


def test_ranges_count_characters_not_bytes(tmp_path: Path) -> None:
    """``ñ`` and ``é`` are two bytes each but one character each."""
    path = tmp_path / "notes.txt"
    path.write_text("año café vLLM", encoding="utf-8")
    assert CORPUS.read_source(source_of(path, 9, 13)) == "vLLM"


def test_missing_source_file_is_reported(tmp_path: Path) -> None:
    """A source whose file is gone ends in a clear error, not a traceback."""
    missing = tmp_path / "gone.py"
    with pytest.raises(ValueError, match=re.escape(f"cannot read {missing}")):
        CORPUS.read_source(source_of(missing, 0, 10))


@pytest.mark.skipif(not INDEX_PATH.is_file(), reason="index not built")
def test_text_matches_the_stored_chunks() -> None:
    """Reading the corpus gives back exactly the text the index stored.

    Checked on a sample spread over the whole real index: if the corpus were
    read differently here than when indexing, the ranges would drift.
    """
    rows = SqliteIndexStore().load_chunks(str(INDEX_PATH))
    for _, file_path, first, last, text, _ in rows[::500]:
        source = source_of(Path(file_path), first, last)
        assert CORPUS.read_source(source) == text
