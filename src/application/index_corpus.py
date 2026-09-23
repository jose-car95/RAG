"""Use case that turns the raw corpus into a persisted chunk index."""

from tqdm import tqdm

from src.adapters.corpus import find_corpus_files
from src.adapters.sqlite_index import save_chunks
from src.domain.chunking import chunker_for


def run_index(raw_directory: str, max_chunk_size: int, index_path: str) -> int:
    """Chunk every corpus file and store the chunks in the index.

    Args:
        raw_directory: Root directory of the corpus to read.
        max_chunk_size: Maximum width in characters of a chunk.
        index_path: Where the SQLite index is written.

    Returns:
        The number of chunks stored.

    Raises:
        ValueError: If the corpus cannot be read or the index written.
    """
    files = find_corpus_files(raw_directory)
    chunks: list[tuple[str, int, int, str]] = []
    for path in tqdm(files, desc="Indexing", unit="file"):
        text = path.read_text(encoding="utf-8")
        chunker = chunker_for(path.suffix)
        for first, last in chunker(text, max_chunk_size):
            chunks.append((str(path), first, last, text[first:last]))

    save_chunks(chunks, index_path)
    return len(chunks)
