"""Read the corpus: the files on disk that the index is built from."""

from pathlib import Path

from src.application.ports.corpus_reader import CorpusReader
from src.domain.models import MinimalSource


# Matches the two chunking strategies of the subject: Python code and
# Markdown/plain text.
INDEXABLE_SUFFIXES = (".py", ".md", ".txt")


class FileCorpus(CorpusReader):
    """The ``CorpusReader`` port on the files of a folder on disk."""

    def find_files(self, raw_directory: str) -> list[Path]:
        """Find every indexable file under ``raw_directory``, in sorted order.

        Paths keep the prefix exactly as given (``data/raw/...``) because
        the grader compares ``file_path`` verbatim, and they are sorted so
        that every machine indexes the files in the same order.

        Args:
            raw_directory: Folder of the corpus.

        Returns:
            The ``.py``, ``.md`` and ``.txt`` files found at any depth.

        Raises:
            ValueError: If the folder does not exist or has no indexable file.
        """
        corpus_root = Path(raw_directory)
        if not corpus_root.is_dir():
            raise ValueError(f"corpus folder not found: {raw_directory}")

        files: list[Path] = []
        for candidate in corpus_root.rglob("*"):
            if candidate.is_file() and candidate.suffix in INDEXABLE_SUFFIXES:
                files.append(candidate)

        if not files:
            raise ValueError(f"no indexable files in {raw_directory}")

        return sorted(files)

    def read_text(self, path: Path) -> str:
        """Read a whole corpus file as UTF-8.

        Args:
            path: One of the files from ``find_files``.

        Returns:
            Its text.
        """
        return path.read_text(encoding="utf-8")

    def read_source(self, source: MinimalSource) -> str:
        """Read the text a source points to, from its corpus file.

        The file is read exactly as ``read_text`` reads it for the index,
        so the stored character range cuts the same text.

        Args:
            source: A file path and a character range, end excluded.

        Returns:
            The text inside that range.

        Raises:
            ValueError: If the file cannot be read.
        """
        try:
            text = Path(source.file_path).read_text(encoding="utf-8")
        except OSError as error:
            raise ValueError(f"cannot read {source.file_path}") from error
        return text[source.first_character_index:source.last_character_index]
