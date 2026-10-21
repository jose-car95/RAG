"""Port: where the chunk index is kept between ``index`` and a search."""

from typing import Protocol

# A stored chunk: id, file path, first and last character index, and text.
StoredChunk = tuple[int, str, int, int, str]
# A chunk to store, without the id the store assigns.
NewChunk = tuple[str, int, int, str]


class IndexStore(Protocol):
    """Save the chunks once, load them for every search.

    A port because the index is an outside resource: today a SQLite file,
    tomorrow a cache in front of it (bonus) without touching the use cases.
    """

    def save_chunks(self, chunks: list[NewChunk], index_path: str) -> None:
        """Replace the whole index with these chunks.

        Args:
            chunks: File path, first and last character index and text of
                each chunk, in corpus order.
            index_path: Where the index lives.

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
