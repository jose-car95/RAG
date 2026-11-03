"""Port: where the vectors are kept between runs."""

from typing import Protocol

from src.application.ports.embedder import Vectors


class VectorStore(Protocol):
    """Vectors keyed by the hash of their text, so equal texts share one."""

    def known_hashes(self, vectors_path: str) -> set[str]:
        """List the text hashes that already have a vector.

        Args:
            vectors_path: The vector file.

        Returns:
            The stored hashes; empty if the file is missing or unreadable.
        """
        ...

    def save_vectors(
        self, vectors_path: str, hashes: list[str], vectors: Vectors
    ) -> None:
        """Store one vector per hash, replacing any vector already there.

        Args:
            vectors_path: The vector file, created if missing.
            hashes: The text hashes, in the order of ``vectors``.
            vectors: One row per hash.

        Raises:
            ValueError: If the file cannot be written.
        """
        ...
