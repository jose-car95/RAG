"""Use case that turns the raw corpus into a persisted chunk index."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from tqdm import tqdm

from src.application.use_cases.shared.indexing_code import code_version
from src.application.use_cases.shared.progress import status
from src.application.ports.corpus_reader import CorpusReader
from src.application.ports.index_store import IndexStore, NewChunk
from src.domain.chunking import chunk_context, chunker_for, definition_spans


# The subject's ceiling for a retrieved source, in characters. The guard,
# the error message and the CLI default all read it from here.
MAX_CHUNK_SIZE: int = 2000


@dataclass(frozen=True)
class IndexReport:
    """What one ``run_index`` call did, for the CLI to summarise.

    A use case returns data instead of printing, so the same numbers can
    feed the CLI summary, a test or the HTTP API.

    Attributes:
        file_count: Corpus files read.
        changed_file_count: Files that were (re)chunked now.
        chunk_count: Chunks in the index afterwards.
        new_chunk_count: Chunks written now; 0 when nothing changed.
        removed_chunk_count: Stored chunks deleted now because their file
            changed or left the corpus; a changed file's chunks are deleted
            and written again, so they count in both numbers.
        removed_file_count: Files that left the corpus.
        average_chunk_size: Mean characters of the chunks written now, or of
            the stored ones when nothing was written.
        largest_chunk_size: Largest of those chunks, in characters.
        up_to_date: True when the index already matched the corpus and was
            left untouched.
        seconds: Seconds spent in each named phase.
    """

    file_count: int
    changed_file_count: int
    chunk_count: int
    new_chunk_count: int
    removed_chunk_count: int
    removed_file_count: int
    average_chunk_size: float
    largest_chunk_size: int
    up_to_date: bool
    seconds: dict[str, float]


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
    index_store: IndexStore,
    incremental: bool = False
) -> IndexReport:
    """Chunk the corpus and store the chunks in the index.

    By default the index is rebuilt from scratch: every file is chunked and
    the previous index is replaced, which also gives the file back its
    minimal size. With ``incremental`` on, the stored fingerprints are read
    and only the files whose fingerprint differs are re-chunked (bonus); when
    nothing can be reused (first run, old index, new chunk size) that path
    still rebuilds from scratch. A full rebuild always records the
    fingerprints, so a later ``incremental`` run can reuse them.

    Args:
        raw_directory: Root directory of the corpus to read.
        max_chunk_size: Maximum width in characters of a chunk, from 1 to
            ``MAX_CHUNK_SIZE``.
        index_path: Where the index is written.
        corpus: Finds and reads the corpus files.
        index_store: Stores the chunks.
        incremental: Re-chunk only the files that changed since the last
            index, instead of rebuilding from scratch.

    Returns:
        An ``IndexReport`` with the counts, sizes and seconds per phase.

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

    seconds: dict[str, float] = {}
    started = perf_counter()
    files = corpus.find_files(raw_directory)
    code = code_version()
    # A full rebuild ignores the stored fingerprints: with none to match,
    # every file is chunked and the save_chunks path below replaces the index.
    stored = index_store.load_fingerprints(index_path) if incremental else {}
    fingerprints: dict[str, str] = {}
    # Only the texts that need chunking are kept, so an up-to-date index
    # chunks nothing and shows no chunking bar.
    pending: dict[str, str] = {}

    for path in tqdm(files, desc="Scanning corpus", unit="file"):
        file_path = str(path)
        text = corpus.read_text(path)
        fingerprints[file_path] = fingerprint(text, max_chunk_size, code)
        if stored.get(file_path) != fingerprints[file_path]:
            pending[file_path] = text
    seconds["scan"] = perf_counter() - started

    removed = [
        file_path
        for file_path, old in stored.items()
        if fingerprints.get(file_path) != old
    ]
    if fingerprints and not pending and not removed:
        return up_to_date_report(
            index_path, index_store, len(files), seconds
        )

    started = perf_counter()
    chunks: list[NewChunk] = []
    bar = tqdm(pending.items(), desc="Chunking", unit="file")
    for file_path, text in bar:
        path = Path(file_path)
        chunker = chunker_for(path.suffix)
        # Context gives a mid-document chunk back what it would otherwise lose
        # (its class or its headings) plus the file path; the domain builds it
        # so the code version of #97 covers every rule that shapes the index.
        is_python = path.suffix == ".py"
        spans = definition_spans(text) if is_python else []
        for first, last in chunker(text, max_chunk_size):
            context = chunk_context(text, file_path, first, spans, is_python)
            chunks.append((file_path, first, last, text[first:last], context))
        bar.set_postfix(chunks=len(chunks))
    seconds["chunk"] = perf_counter() - started

    started = perf_counter()
    # No bar here: SQLite writes the chunks in one transaction, so there is
    # no per-item progress to show, only a message so it does not look hung.
    status(f"Writing {len(chunks)} chunks to SQLite...")
    changed = {file_path: fingerprints[file_path] for file_path in pending}
    # Counted before the write, from the old rows; a first build has none.
    old_count = len(index_store.load_chunks(index_path)) if stored else 0
    if len(changed) == len(fingerprints):
        index_store.save_chunks(chunks, index_path, fingerprints)
        chunk_count = len(chunks)
    else:
        chunk_count = index_store.update_files(
            index_path, removed, chunks, changed
        )
    seconds["write"] = perf_counter() - started
    # The old rows plus the new ones minus what is left is what was deleted.
    removed_chunks = old_count + len(chunks) - chunk_count
    gone_files = [name for name in removed if name not in fingerprints]
    sizes = [len(chunk[3]) for chunk in chunks]
    return IndexReport(
        file_count=len(files),
        changed_file_count=len(pending),
        chunk_count=chunk_count,
        new_chunk_count=len(chunks),
        removed_chunk_count=removed_chunks,
        removed_file_count=len(gone_files),
        average_chunk_size=sum(sizes) / len(sizes) if sizes else 0.0,
        largest_chunk_size=max(sizes, default=0),
        up_to_date=False,
        seconds=seconds
    )


def up_to_date_report(
    index_path: str,
    index_store: IndexStore,
    file_count: int,
    seconds: dict[str, float]
) -> IndexReport:
    """Describe an index that already matches the corpus, writing nothing.

    Args:
        index_path: The untouched index.
        index_store: Reads the stored chunks for the statistics.
        file_count: Corpus files scanned.
        seconds: Seconds of the phases already run.

    Returns:
        A report with ``up_to_date`` set and no new chunks.
    """
    sizes = [last - first for _, _, first, last, _, _ in
             index_store.load_chunks(index_path)]
    status(f"Index up to date: {file_count} files, {len(sizes)} chunks, "
           "nothing to do")
    return IndexReport(
        file_count=file_count,
        changed_file_count=0,
        chunk_count=len(sizes),
        new_chunk_count=0,
        removed_chunk_count=0,
        removed_file_count=0,
        average_chunk_size=sum(sizes) / len(sizes) if sizes else 0.0,
        largest_chunk_size=max(sizes, default=0),
        up_to_date=True,
        seconds=seconds
    )
