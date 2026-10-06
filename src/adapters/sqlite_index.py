"""SQLite storage for the chunk index."""

import sqlite3
from contextlib import closing
from pathlib import Path


CREATE_TABLE_SQL = """
    CREATE TABLE chunks (
        id INTEGER PRIMARY KEY,
        file_path TEXT NOT NULL,
        first_character_index INTEGER NOT NULL,
        last_character_index INTEGER NOT NULL,
        text TEXT NOT NULL
    )
"""
INSERT_CHUNK_SQL = """
    INSERT INTO chunks (
        file_path,
        first_character_index,
        last_character_index,
        text
    )
    VALUES (?, ?, ?, ?)
"""
SELECT_CHUNKS_SQL = """
    SELECT id, file_path, first_character_index, last_character_index, text
    FROM chunks
    ORDER BY id
"""


def save_chunks(
    chunks: list[tuple[str, int, int, str]],
    index_path: str
) -> None:
    """Store every chunk in a freshly created SQLite index.

    The index file is removed before being rebuilt: SQLite marks deleted
    pages as reusable but never returns them to the operating system, so
    reusing the file would keep the size of a previous, bigger index.

    Args:
        chunks: Tuples of file path, first character index, last character
            index and chunk text, in corpus order.
        index_path: Where the database is written; missing parent
            directories are created.

    Raises:
        ValueError: If the index cannot be created or written.
    """
    try:
        index_file = Path(index_path)
        index_file.unlink(missing_ok=True)
        index_file.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(index_file)) as connection, connection:
            connection.execute(CREATE_TABLE_SQL)
            connection.executemany(INSERT_CHUNK_SQL, chunks)

    except (sqlite3.Error, OSError) as error:
        raise ValueError(f"cannot write index: {index_path}") from error


def load_chunks(index_path: str) -> list[tuple[int, str, int, int, str]]:
    """Read every stored chunk, in index order.

    The file is checked before connecting because ``sqlite3.connect``
    creates the database it cannot find, which would leave an empty index
    behind and report a missing table instead of a missing index.

    The rows are materialised into a list on purpose: returning the cursor
    would hand the caller a closed connection.

    Args:
        index_path: Path of the SQLite index.

    Returns:
        One tuple per chunk: id, file path, first and last character index,
        and text.

    Raises:
        ValueError: If the index does not exist or cannot be read.
    """
    index_file = Path(index_path)
    if not index_file.is_file():
        raise ValueError(f"index not found: {index_path}; run index first")
    try:
        with closing(sqlite3.connect(index_file)) as connection:
            return list(connection.execute(SELECT_CHUNKS_SQL))
    except (sqlite3.Error, OSError) as error:
        raise ValueError(f"cannot read index: {index_path}") from error
