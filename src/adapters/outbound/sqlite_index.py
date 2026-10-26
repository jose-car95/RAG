"""SQLite storage for the chunk index."""

import sqlite3
from contextlib import closing
from pathlib import Path

from src.application.ports.index_store import (
    IndexStore,
    NewChunk,
    StoredChunk
)

CREATE_FILES_TABLE_SQL = """
    CREATE TABLE files (
        file_path TEXT PRIMARY KEY,
        fingerprint TEXT NOT NULL
    )
"""
INSERT_FILE_SQL = "INSERT INTO files (file_path, fingerprint) VALUES (?, ?)"
SELECT_FILES_SQL = "SELECT file_path, fingerprint FROM files"
DELETE_FILE_SQL = "DELETE FROM files WHERE file_path = ?"
CREATE_CHUNKS_TABLE_SQL = """
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
DELETE_CHUNKS_SQL = "DELETE FROM chunks WHERE file_path = ?"
COUNT_CHUNKS_SQL = "SELECT COUNT(*) FROM chunks"


def find_index_file(index_path: str) -> Path:
    """Return the index file, or say it is missing.

    Shared by every read so the message the user sees lives in one place.

    Args:
        index_path: Path of the SQLite index.

    Returns:
        The index file.

    Raises:
        ValueError: If there is no file at that path.
    """
    index_file = Path(index_path)
    if not index_file.is_file():
        raise ValueError(
            f"index not found: {index_path}; run index first"
        )
    return index_file


class SqliteIndexStore(IndexStore):
    """The ``IndexStore`` port on a SQLite file with two tables.

    ``chunks`` holds one row per chunk; ``files`` one row per indexed file
    with its fingerprint, for incremental indexing.
    """

    def save_chunks(
        self,
        chunks: list[NewChunk],
        index_path: str,
        fingerprints: dict[str, str]
    ) -> None:
        """Store every chunk in a freshly created SQLite index.

        The index file is removed before being rebuilt: SQLite marks deleted
        pages as reusable but never returns them to the operating system, so
        reusing the file would keep the size of a previous, bigger index.

        Args:
            chunks: Tuples of file path, first character index, last
                character index and chunk text, in corpus order.
            index_path: Where the database is written; missing parent
                directories are created.
            fingerprints: File path to fingerprint of every indexed file.

        Raises:
            ValueError: If the index cannot be created or written.
        """
        try:
            index_file = Path(index_path)
            index_file.unlink(missing_ok=True)
            index_file.parent.mkdir(parents=True, exist_ok=True)
            with (
                closing(sqlite3.connect(index_file)) as connection,
                connection
            ):
                connection.execute(CREATE_CHUNKS_TABLE_SQL)
                connection.executemany(INSERT_CHUNK_SQL, chunks)
                connection.execute(CREATE_FILES_TABLE_SQL)
                connection.executemany(INSERT_FILE_SQL, fingerprints.items())

        except (sqlite3.Error, OSError) as error:
            raise ValueError(f"cannot write index: {index_path}") from error

    def load_fingerprints(self, index_path: str) -> dict[str, str]:
        """Read the fingerprint of every indexed file.

        Any database error means "nothing to reuse", not a user error: an
        index from before the ``files`` table, or a broken one, is simply
        rebuilt by the caller.

        Args:
            index_path: Path of the SQLite index.

        Returns:
            File path to fingerprint, or an empty dict.
        """
        index_file = Path(index_path)
        if not index_file.is_file():
            return {}
        try:
            with closing(sqlite3.connect(index_file)) as connection:
                return dict(connection.execute(SELECT_FILES_SQL))
        except sqlite3.Error:
            return {}

    def update_files(
        self,
        index_path: str,
        removed: list[str],
        chunks: list[NewChunk],
        fingerprints: dict[str, str]
    ) -> int:
        """Replace the chunks of some files inside one transaction.

        Rows are deleted before inserting, so a modified file, which is both
        in ``removed`` and in ``fingerprints``, never clashes with its own
        primary key. The file keeps the space of deleted rows for reuse.

        Args:
            index_path: Path of an existing SQLite index.
            removed: Files whose chunks and fingerprint are dropped.
            chunks: New chunks of the modified and new files.
            fingerprints: New fingerprint of those files.

        Returns:
            The number of chunks in the index afterwards.

        Raises:
            ValueError: If the index cannot be written.
        """
        try:
            with (
                closing(sqlite3.connect(index_path)) as connection,
                connection
            ):
                gone = [(file_path,) for file_path in removed]
                connection.executemany(DELETE_CHUNKS_SQL, gone)
                connection.executemany(DELETE_FILE_SQL, gone)
                connection.executemany(INSERT_CHUNK_SQL, chunks)
                connection.executemany(INSERT_FILE_SQL, fingerprints.items())
                count: int = connection.execute(COUNT_CHUNKS_SQL).fetchone()[0]
            return count
        except (sqlite3.Error, OSError) as error:
            raise ValueError(f"cannot write index: {index_path}") from error

    def load_chunks(self, index_path: str) -> list[StoredChunk]:
        """Read every stored chunk, in index order.

        The file is checked before connecting because ``sqlite3.connect``
        creates the database it cannot find, which would leave an empty
        index behind and report a missing table instead of a missing index.

        The rows are materialised into a list on purpose: returning the
        cursor would hand the caller a closed connection.

        Args:
            index_path: Path of the SQLite index.

        Returns:
            One tuple per chunk: id, file path, first and last character
            index, and text.

        Raises:
            ValueError: If the index does not exist or cannot be read.
        """
        index_file = find_index_file(index_path)
        try:
            with closing(sqlite3.connect(index_file)) as connection:
                return list(connection.execute(SELECT_CHUNKS_SQL))
        except (sqlite3.Error, OSError) as error:
            raise ValueError(f"cannot read index: {index_path}") from error

    def index_version(self, index_path: str) -> tuple[int, int]:
        """Return the modification time and size of the index file.

        ``index`` deletes and recreates the file, so the modification time
        changes on every rebuild; the size is a second, cheap witness.

        Args:
            index_path: Path of the SQLite index.

        Returns:
            Modification time in nanoseconds and size in bytes.

        Raises:
            ValueError: If the index does not exist.
        """
        status = find_index_file(index_path).stat()
        return status.st_mtime_ns, status.st_size
