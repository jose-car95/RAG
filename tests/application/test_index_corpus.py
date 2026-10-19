"""Tests for the index use case: chunk the corpus and store it in SQLite."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import cast

import pytest

from src.adapters.outbound.corpus import FileCorpus
from src.adapters.outbound.sqlite_index import SqliteIndexStore
from src.application.use_cases.index_corpus import run_index

CORPUS = FileCorpus()
STORE = SqliteIndexStore()

PY_FILE = (
    "import os\n"
    "\n"
    "\n"
    "def first() -> int:\n"
    "    return 1\n"
    "\n"
    "\n"
    "def second() -> int:\n"
    "    return 2\n"
)
MD_FILE = "# A\nuno\n\n# B\ndos\n"
INVALID_SIZE_MESSAGE = (
    "^max_chunk_size must be an integer between 1 and 2000$"
)


def make_corpus(root: Path) -> None:
    """Create a small corpus: one Python file, one Markdown file and noise.

    Args:
        root: Folder where the corpus is created.
    """
    (root / "pkg").mkdir(parents=True, exist_ok=True)
    (root / "pkg" / "a.py").write_text(PY_FILE, encoding="utf-8")
    (root / "b.md").write_text(MD_FILE, encoding="utf-8")
    (root / "c.json").write_text("{}", encoding="utf-8")


def read_rows(index_path: Path) -> list[tuple[str, int, int, str]]:
    """Read every stored chunk, ordered by file and position.

    Args:
        index_path: Path of the SQLite index.

    Returns:
        One tuple per chunk: path, first index, last index and text.
    """
    query = (
        "SELECT file_path, first_character_index, last_character_index, text"
        " FROM chunks ORDER BY file_path, first_character_index"
    )
    with closing(sqlite3.connect(index_path)) as connection:
        return list(connection.execute(query))


def test_chunks_are_stored_with_their_text(tmp_path: Path) -> None:
    """Every row keeps the corpus path and the exact text of its range."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    index_path = tmp_path / "index.db"

    chunk_count = run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)

    rows = read_rows(index_path)
    assert chunk_count == len(rows)
    for file_path, first, last, text in rows:
        source = Path(file_path).read_text(encoding="utf-8")
        assert text == source[first:last]
    assert {Path(row[0]).name for row in rows} == {"a.py", "b.md"}


def test_each_file_uses_the_strategy_of_its_extension(tmp_path: Path) -> None:
    """Python is cut at definitions and Markdown at headings."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    index_path = tmp_path / "index.db"

    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)

    rows = read_rows(index_path)
    python_rows = [row for row in rows if row[0].endswith("a.py")]
    markdown_rows = [row for row in rows if row[0].endswith("b.md")]
    assert [(row[1], row[2]) for row in python_rows] == [
        (0, 12), (12, 47), (47, 81)
    ]
    assert [(row[1], row[2]) for row in markdown_rows] == [(0, 9), (9, 17)]


def test_reindexing_does_not_duplicate_chunks(tmp_path: Path) -> None:
    """Running the index twice rebuilds it instead of appending."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    index_path = tmp_path / "index.db"

    first_count = run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)
    second_count = run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)

    assert first_count == second_count == len(read_rows(index_path))


def test_missing_index_folders_are_created(tmp_path: Path) -> None:
    """Folders of the index path that do not exist yet are created."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    index_path = tmp_path / "new" / "nested" / "index.db"

    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)

    assert index_path.is_file()


def test_missing_corpus_leaves_no_index(tmp_path: Path) -> None:
    """A missing corpus fails before creating any database."""
    index_path = tmp_path / "index.db"

    with pytest.raises(ValueError, match="^corpus folder not found: "):
        run_index(str(tmp_path / "nope"), 2000, str(index_path), CORPUS, STORE)

    assert not index_path.exists()


def test_unwritable_index_path_is_reported(tmp_path: Path) -> None:
    """An index path that cannot be written ends in a clear error."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    blocking_file = tmp_path / "a_file.txt"
    blocking_file.write_text("not a folder", encoding="utf-8")
    index_path = blocking_file / "index.db"

    with pytest.raises(
        ValueError, match=f"^cannot write index: {index_path}$"
    ):
        run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)


def test_index_file_matches_its_current_content(tmp_path: Path) -> None:
    """A rebuilt index does not keep the size of a bigger, older one.

    SQLite never returns space to the file system, so an index that once
    held many chunks would stay big forever unless it is rebuilt from
    scratch.
    """
    index_path = tmp_path / "index.db"
    many = [
        (f"data/raw/file_{number}.py", 0, 1000, "x" * 1000)
        for number in range(2000)
    ]
    few = [("data/raw/file_0.py", 0, 10, "x" * 10)]

    STORE.save_chunks(many, str(index_path))
    big_size = index_path.stat().st_size
    STORE.save_chunks(few, str(index_path))

    assert index_path.stat().st_size < big_size
    with closing(sqlite3.connect(index_path)) as connection:
        free_pages = connection.execute("PRAGMA freelist_count").fetchone()[0]
    assert free_pages == 0


@pytest.mark.parametrize(
    "max_chunk_size",
    [0, -5, "abc", 2.5, True, 2001],
    ids=["zero", "negative", "text", "float", "bool", "above-limit"],
)
def test_invalid_max_chunk_size_is_rejected(
    tmp_path: Path, max_chunk_size: object
) -> None:
    """Only an integer between 1 and 2000 is accepted, and nothing is written.

    Args:
        tmp_path: Temporary folder provided by pytest.
        max_chunk_size: Rejected value, as Fire would pass it.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    index_path = tmp_path / "index.db"

    with pytest.raises(ValueError, match=INVALID_SIZE_MESSAGE):
        # Fire can pass text, a float or a bool; mypy cannot see that.
        run_index(
            str(corpus),
            cast(int, max_chunk_size),
            str(index_path),
            CORPUS,
            STORE
        )

    assert not index_path.exists()


def test_a_rejected_size_keeps_the_previous_index(tmp_path: Path) -> None:
    """The stored index survives a call with an invalid chunk width.

    The index file is deleted before being rebuilt, so validating late would
    destroy a good index because of a mistyped number.

    Args:
        tmp_path: Temporary folder provided by pytest.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    index_path = tmp_path / "index.db"
    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)
    stored = read_rows(index_path)

    with pytest.raises(ValueError, match=INVALID_SIZE_MESSAGE):
        run_index(str(corpus), 0, str(index_path), CORPUS, STORE)

    assert read_rows(index_path) == stored


def test_chunks_respect_a_smaller_size(tmp_path: Path) -> None:
    """A valid size below the default is honoured by every stored chunk.

    Args:
        tmp_path: Temporary folder provided by pytest.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    index_path = tmp_path / "index.db"

    run_index(str(corpus), 20, str(index_path), CORPUS, STORE)

    widths = [last - first for _, first, last, _ in read_rows(index_path)]
    assert widths and max(widths) <= 20


def test_stored_chunks_are_read_back_with_their_location() -> None:
    """``load_chunks`` returns what ``save_chunks`` wrote, ids included."""
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        index_path = str(Path(folder) / "index.db")
        chunks = [
            ("data/raw/a.py", 0, 5, "alpha"),
            ("data/raw/b.md", 5, 9, "beta"),
        ]
        STORE.save_chunks(chunks, index_path)

        rows = STORE.load_chunks(index_path)

    stored = [(path, first, last, text)
              for _, path, first, last, text in rows]
    assert stored == chunks
    assert [chunk_id for chunk_id, *_ in rows] == [1, 2]


def test_loading_a_missing_index_creates_no_file(tmp_path: Path) -> None:
    """A missing index is reported without leaving an empty database."""
    index_path = tmp_path / "nope" / "index.db"
    message = f"^index not found: {index_path}; run index first$"

    with pytest.raises(ValueError, match=message):
        STORE.load_chunks(str(index_path))

    assert not index_path.exists()
