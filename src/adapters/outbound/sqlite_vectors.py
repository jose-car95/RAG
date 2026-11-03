"""SQLite storage for the chunk embeddings."""

import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np

from src.application.ports.embedder import Vectors
from src.application.ports.vector_store import VectorStore


CREATE_VECTORS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS vectors (
        text_hash TEXT PRIMARY KEY,
        vector BLOB NOT NULL
    )
"""
INSERT_VECTOR_SQL = (
    "INSERT OR REPLACE INTO vectors (text_hash, vector) VALUES (?, ?)"
)
SELECT_VECTORS_SQL = "SELECT text_hash, vector FROM vectors"
SELECT_HASHES_SQL = "SELECT text_hash FROM vectors"


class SqliteVectorStore(VectorStore):
    """A vector store in its own SQLite file, apart from the lexical index.

    The vectors live apart so that rebuilding the lexical index never
    throws away minutes of embedding work.
    """

    def known_hashes(self, vectors_path: str) -> set[str]:
        """List the text hashes that already have a vector.

        Args:
            vectors_path: The vector file.

        Returns:
            The stored hashes; empty if the file is missing or unreadable,
            so every text is embedded again.
        """
        if not Path(vectors_path).is_file():
            return set()
        try:
            with closing(sqlite3.connect(vectors_path)) as connection:
                return {
                    text_hash
                    for (text_hash,) in connection.execute(SELECT_HASHES_SQL)
                }
        except sqlite3.Error:
            return set()

    def save_vectors(
        self, vectors_path: str, hashes: list[str], vectors: Vectors
    ) -> None:
        """Store one vector per hash, replacing any vector already there.

        Each call is one transaction: an interrupted run keeps the batches
        already saved.

        Args:
            vectors_path: The vector file, created if missing.
            hashes: The text hashes, in the order of ``vectors``.
            vectors: One row per hash.

        Raises:
            ValueError: If the file cannot be written.
        """
        try:
            vectors_file = Path(vectors_path)
            vectors_file.parent.mkdir(parents=True, exist_ok=True)
            with (
                closing(sqlite3.connect(vectors_file)) as connection,
                connection
            ):
                connection.execute(CREATE_VECTORS_TABLE_SQL)
                connection.executemany(
                    INSERT_VECTOR_SQL,
                    zip(hashes, (vector.tobytes() for vector in vectors))
                )
        except (sqlite3.Error, OSError) as error:
            raise ValueError(
                f"cannot write embeddings: {vectors_path}"
            ) from error

    def load_vectors(self, vectors_path: str) -> dict[str, Vectors]:
        """Load every stored vector, keyed by its text hash.

        Args:
            vectors_path: The vector file.

        Returns:
            Text hash to its vector; empty if the file is missing or
            unreadable, so a semantic search finds nothing to rank.
        """
        if not Path(vectors_path).is_file():
            return {}
        try:
            with closing(sqlite3.connect(vectors_path)) as connection:
                return {
                    text_hash: np.frombuffer(blob, dtype=np.float32)
                    for text_hash, blob in connection.execute(
                        SELECT_VECTORS_SQL
                    )
                }
        except sqlite3.Error:
            return {}
