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
