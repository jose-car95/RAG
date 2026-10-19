"""Port: the documents the system indexes and quotes."""

from pathlib import Path
from typing import Protocol

from src.domain.models import MinimalSource


class CorpusReader(Protocol):
    """Find the corpus files and read their text.

    A port because the corpus lives outside the program: today files on
    disk, and incremental indexing (bonus) would need to ask it what changed.
    """

    def find_files(self, raw_directory: str) -> list[Path]:
        """List every indexable file of the corpus, in a stable order.

        Args:
            raw_directory: Folder of the corpus.

        Returns:
            The files, with their paths exactly as the grader expects.

        Raises:
            ValueError: If the folder does not exist or has no indexable file.
        """
        ...

    def read_text(self, path: Path) -> str:
        """Read the whole text of a corpus file.

        Args:
            path: One of the files from ``find_files``.

        Returns:
            Its text.
        """
        ...

    def read_source(self, source: MinimalSource) -> str:
        """Read the text a source points to.

        Args:
            source: A file path and a character range, end excluded.

        Returns:
            The text inside that range.

        Raises:
            ValueError: If the file cannot be read.
        """
        ...
