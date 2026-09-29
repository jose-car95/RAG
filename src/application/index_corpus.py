"""Use case that turns the raw corpus into a persisted chunk index."""

from tqdm import tqdm

from src.adapters.corpus import find_corpus_files
from src.adapters.sqlite_index import save_chunks
from src.domain.chunking import chunker_for


# The subject's ceiling for a retrieved source, in characters. The guard,
# the error message and the CLI default all read it from here.
MAX_CHUNK_SIZE: int = 2000


def run_index(raw_directory: str, max_chunk_size: int, index_path: str) -> int:
    """Chunk every corpus file and store the chunks in the index.

    Args:
        raw_directory: Root directory of the corpus to read.
        max_chunk_size: Maximum width in characters of a chunk, from 1 to
            ``MAX_CHUNK_SIZE``.
        index_path: Where the SQLite index is written.

    Returns:
        The number of chunks stored.

    Raises:
        ValueError: If ``max_chunk_size`` is out of range, or the corpus
            cannot be read, or the index cannot be written. The size is
            checked first, so a rejected call leaves the stored index
            untouched.
    """
    if (
        isinstance(max_chunk_size, bool)
        or not isinstance(max_chunk_size, int)
        or max_chunk_size <= 0
        or max_chunk_size > MAX_CHUNK_SIZE
    ):
        raise ValueError(
            f"max_chunk_size must be an integer between 1 and {MAX_CHUNK_SIZE}"
        )
    files = find_corpus_files(raw_directory)
    chunks: list[tuple[str, int, int, str]] = []
    for path in tqdm(files, desc="Indexing", unit="file"):
        text = path.read_text(encoding="utf-8")
        chunker = chunker_for(path.suffix)
        for first, last in chunker(text, max_chunk_size):
            chunks.append((str(path), first, last, text[first:last]))

    save_chunks(chunks, index_path)
    return len(chunks)
