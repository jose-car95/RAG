"""Port: where the chunk index is kept between ``index`` and a search."""

from typing import Protocol

from src.domain.bm25 import CorpusIndex


# A stored chunk: id, file path, first and last character index, and text.
StoredChunk = tuple[int, str, int, int, str]
# A chunk to store, without the id the store assigns.
NewChunk = tuple[str, int, int, str]


class IndexStore(Protocol):
    """Save the chunks once, load them for every search.

    A port because the index is an outside resource: today a SQLite file,
    tomorrow a cache in front of it (bonus) without touching the use cases.
    It also keeps a fingerprint per file, so ``index`` can skip what did not
    change.
    """

    def save_chunks(
        self,
        chunks: list[NewChunk],
        index_path: str,
        fingerprints: dict[str, str]
    ) -> None:
        """Replace the whole index with these chunks.

        Args:
            chunks: File path, first and last character index and text of
                each chunk, in corpus order.
            index_path: Where the index lives.
            fingerprints: File path to the fingerprint of its text, so the
                next ``index`` can tell which files changed.

        Raises:
            ValueError: If the index cannot be written.
        """
        ...

    def load_fingerprints(self, index_path: str) -> dict[str, str]:
        """Read the fingerprint of every indexed file.

        Args:
            index_path: Where the index lives.

        Returns:
            File path to fingerprint; empty when there is nothing to reuse
            (no index, or one that cannot be read), which means a full
            rebuild.
        """
        ...

    def update_files(
        self,
        index_path: str,
        removed: list[str],
        chunks: list[NewChunk],
        fingerprints: dict[str, str]
    ) -> int:
        """Change only some files of an existing index, all or nothing.

        Args:
            index_path: Where the index lives.
            removed: Files whose chunks and fingerprint are dropped: the
                modified and the deleted ones.
            chunks: The new chunks of the modified and new files.
            fingerprints: The new fingerprint of those same files.

        Returns:
            How many chunks the index holds afterwards.

        Raises:
            ValueError: If the index cannot be written.
        """
        ...

    def load_chunks(self, index_path: str) -> list[StoredChunk]:
        """Read every stored chunk, in index order.

        Args:
            index_path: Where the index lives.

        Returns:
            One tuple per chunk.

        Raises:
            ValueError: If the index does not exist or cannot be read.
        """
        ...

    def index_version(self, index_path: str) -> tuple[int, int]:
        """Tell whether the index changed, without reading it.

        Args:
            index_path: Where the index lives.

        Returns:
            A value that changes whenever the index is rebuilt.

        Raises:
            ValueError: If the index does not exist.
        """
        ...

    def load_built_index(
        self, index_path: str, version: tuple[int, int]
    ) -> CorpusIndex | None:
        """Return the index built by an earlier process, if still valid.

        Args:
            index_path: Where the index lives.
            version: The current ``index_version`` of the index.

        Returns:
            The built index, or ``None`` when there is none for this version.
        """
        ...

    def save_built_index(
        self, index_path: str, version: tuple[int, int], corpus: CorpusIndex
    ) -> None:
        """Keep a built index for the next process; failing only costs time.

        Args:
            index_path: Where the index lives.
            version: The ``index_version`` the index was built from.
            corpus: The built index.
        """
        ...
