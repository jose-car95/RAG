"""Use case that turns the raw corpus into a persisted chunk index."""

import hashlib

from tqdm import tqdm

from src.application.indexing_code import code_version
from src.application.ports.corpus_reader import CorpusReader
from src.application.ports.index_store import IndexStore, NewChunk
from src.domain.chunking import chunk_context, chunker_for, definition_spans


# The subject's ceiling for a retrieved source, in characters. The guard,
# the error message and the CLI default all read it from here.
MAX_CHUNK_SIZE: int = 2000


def fingerprint(text: str, max_chunk_size: int, code: str) -> str:
    """Summarise what the chunks of a file depend on, in 64 characters.

    The chunks depend on the text, on the chunk size and on the chunking
    code, so all three go into the hash: a new ``--max_chunk_size`` or a new
    chunker changes every fingerprint. SHA-256 of
    the content instead of modification time and size, because archives
    restore old dates and a changed file would then look unchanged.

    Args:
        text: The whole text of a corpus file.
        max_chunk_size: The chunk size it is indexed with.
        code: The ``code_version`` of the indexing code.

    Returns:
        The hexadecimal SHA-256 digest.
    """
    content = f"{code}\n{max_chunk_size}\n{text}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def run_index(
    raw_directory: str,
    max_chunk_size: int,
    index_path: str,
    corpus: CorpusReader,
    index_store: IndexStore
) -> int:
    """Chunk the corpus files that changed and store them in the index.

    Every file is read and fingerprinted; only those whose fingerprint
    differs from the stored one are chunked. When nothing can be reused
    (first run, old index, new chunk size) the index is rebuilt from
    scratch, which also gives the file back its minimal size.

    Args:
        raw_directory: Root directory of the corpus to read.
        max_chunk_size: Maximum width in characters of a chunk, from 1 to
            ``MAX_CHUNK_SIZE``.
        index_path: Where the index is written.
        corpus: Finds and reads the corpus files.
        index_store: Stores the chunks.

    Returns:
        The number of chunks in the index afterwards.

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

    files = corpus.find_files(raw_directory)
    code = code_version()
    stored = index_store.load_fingerprints(index_path)
    fingerprints: dict[str, str] = {}
    chunks: list[NewChunk] = []

    for path in tqdm(files, desc="Indexing", unit="file"):
        file_path = str(path)
        text = corpus.read_text(path)
        fingerprints[file_path] = fingerprint(text, max_chunk_size, code)

        if stored.get(file_path) == fingerprints[file_path]:
            continue

        chunker = chunker_for(path.suffix)
        # Context gives a mid-document chunk back what it would otherwise lose
        # (its class or its headings) plus the file path; the domain builds it
        # so the code version of #97 covers every rule that shapes the index.
        is_python = path.suffix == ".py"
        spans = definition_spans(text) if is_python else []
        for first, last in chunker(text, max_chunk_size):
            context = chunk_context(text, file_path, first, spans, is_python)
            chunks.append((file_path, first, last, text[first:last], context))

    changed = {
        file_path: new
        for file_path, new in fingerprints.items()
        if stored.get(file_path) != new
    }

    if len(changed) == len(fingerprints):
        index_store.save_chunks(chunks, index_path, fingerprints)
        return len(chunks)

    removed = [
        file_path
        for file_path, old in stored.items()
        if fingerprints.get(file_path) != old
    ]
    return index_store.update_files(index_path, removed, chunks, changed)
