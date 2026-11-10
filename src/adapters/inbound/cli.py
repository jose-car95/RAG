"""Command-line interface built with Python Fire.

Each public method of ``RagCli`` becomes a command, and each parameter
becomes a flag with the same name (``k`` becomes ``--k``).
"""

import inspect
import sys
from pathlib import Path
from time import perf_counter

import fire

from src.application.ports.corpus_reader import CorpusReader
from src.application.ports.dataset_store import DatasetStore
from src.application.ports.embedder import EmbedderLoader
from src.application.ports.generator import GeneratorLoader
from src.application.ports.index_store import IndexStore
from src.application.ports.vector_store import VectorStore
from src.application.use_cases.answer import run_answer
from src.application.use_cases.answer_dataset import run_answer_dataset
from src.application.use_cases.evaluate import run_evaluate
from src.application.use_cases.embed_index import (
    EmbedReport,
    run_embed_index,
)
from src.application.use_cases.index_corpus import (
    IndexReport,
    MAX_CHUNK_SIZE,
    run_index
)
from src.application.use_cases.search import (
    run_search,
    run_semantic_search,
    run_hybrid_search
)
from src.application.use_cases.search_dataset import run_search_dataset


# Exit codes follow Unix conventions: 130 is 128 + SIGINT (signal 2), the
# code a program ends with when the user presses Ctrl+C.
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130

# Default store locations, under data/processed/. Kept here so the four
# commands that read the index, and the two that read the vectors, all point
# at the same place and a change touches one line.
DEFAULT_INDEX_PATH = "data/processed/index.db"
DEFAULT_VECTORS_PATH = "data/processed/embeddings.db"


def index_summary(report: IndexReport, index_path: str) -> str:
    """Format what ``index`` did as the lines printed after the main one.

    Args:
        report: What ``run_index`` returned.
        index_path: The index file, to show its size on disk.

    Returns:
        A multi-line summary, one fact per line.
    """
    size = Path(index_path).stat().st_size / 1_000_000
    state = "up to date, nothing to do" if report.up_to_date else "updated"
    phases = ", ".join(
        f"{name} {seconds:.1f}s" for name, seconds in report.seconds.items()
    )
    return (
        f"  Index: {state}\n"
        f"  Files read: {report.file_count} "
        f"({report.changed_file_count} chunked now, "
        f"{report.removed_file_count} left the corpus)\n"
        f"  Chunks: {report.chunk_count} total "
        f"({report.new_chunk_count} written, "
        f"{report.removed_chunk_count} removed), "
        f"average {report.average_chunk_size:.0f} chars, "
        f"largest {report.largest_chunk_size}\n"
        f"  Index file: {size:.1f} MB\n"
        f"  Time: {phases}, total {sum(report.seconds.values()):.1f}s"
    )


def vectors_summary(report: EmbedReport, seconds: float) -> str:
    """Format what the embedding step did, for stderr.

    Args:
        report: What ``run_embed_index`` returned.
        seconds: Seconds the step took.

    Returns:
        A multi-line summary; the orphan line only when there are orphans.
    """
    reused = report.total_count - report.new_count
    lines = [
        f"  Vectors: {report.new_count} new, {reused} reused, "
        f"{seconds:.1f}s"
    ]
    if report.orphaned_count:
        count = report.orphaned_count
        noun = "vector no longer matches" if count == 1 else (
            "vectors no longer match"
        )
        lines.append(
            f"  Orphaned: {count} stored {noun} any chunk text "
            "(kept, not deleted)"
        )
    return "\n".join(lines)


class RagCli:
    """Commands required by the subject, exposed through Fire."""

    def __init__(
        self,
        index_store: IndexStore,
        corpus: CorpusReader,
        datasets: DatasetStore,
        load_generator: GeneratorLoader,
        vector_store: VectorStore,
        load_embedder: EmbedderLoader
    ) -> None:
        """Keep the adapters every command passes to its use case.

        The CLI knows the use cases and the ports, never a concrete adapter:
        ``bootstrap`` hands it the real ones. They are kept in attributes
        that start with ``_`` so that Fire does not list them as commands.

        Args:
            index_store: Where the chunk index is saved and loaded.
            corpus: Finds and reads the corpus files.
            datasets: Reads and writes the JSON files of the subject.
            load_generator: Loads the language model when called.
            vector_store: Where the chunk embeddings are kept.
            load_embedder: Loads the embedding model when called.
        """
        self._index_store = index_store
        self._corpus = corpus
        self._datasets = datasets
        self._load_generator = load_generator
        self._vector_store = vector_store
        self._load_embedder = load_embedder

    def index(
        self,
        max_chunk_size: int = MAX_CHUNK_SIZE,
        raw_directory: str = "data/raw",
        index_path: str = DEFAULT_INDEX_PATH,
        incremental: bool = False,
        semantic: bool = False,
        vectors_path: str = DEFAULT_VECTORS_PATH
    ) -> None:
        """Chunk the corpus and store the chunks in the index.

        By default the index is rebuilt from scratch. Both bonuses are off by
        default: ``--incremental`` re-chunks only the files that changed, and
        ``--semantic`` also stores a semantic vector per chunk.

        Args:
            max_chunk_size: Maximum characters per chunk, from 1 to
                ``MAX_CHUNK_SIZE``.
            raw_directory: Folder of the corpus to index.
            index_path: Where the SQLite index is written.
            incremental: Re-chunk only the files that changed since the last
                index, instead of rebuilding from scratch (bonus).
            semantic: Also store a semantic vector per chunk text (bonus).
            vectors_path: Where the vectors are written.
        """
        # Embeddings are a long, costly bonus: with them on, only what
        # changed is re-indexed, so a second run does not rebuild the index
        # for nothing. Without them, ``index`` still rebuilds from scratch.
        report = run_index(
            raw_directory,
            max_chunk_size,
            index_path,
            self._corpus,
            self._index_store,
            incremental or semantic
        )
        print(
            f"Ingestion complete! Indexed {report.chunk_count} chunks under "
            f"{Path(index_path).parent}/"
        )
        # stderr: stdout keeps only the subject's literal line.
        print(index_summary(report, index_path), file=sys.stderr)

        if semantic:
            started = perf_counter()
            embedded = run_embed_index(
                index_path,
                vectors_path,
                self._index_store,
                self._vector_store,
                self._load_embedder
            )
            print(
                f"Embeddings ready! {embedded.new_count} new of "
                f"{embedded.total_count} chunk texts under "
                f"{Path(vectors_path).parent}/"
            )
            print(vectors_summary(embedded, perf_counter() - started),
                  file=sys.stderr)

    def search(
        self,
        query: str,
        k: int = 10,
        index_path: str = DEFAULT_INDEX_PATH,
        retriever: str = "bm25",
        vectors_path: str = DEFAULT_VECTORS_PATH
    ) -> None:
        """Print the best sources for a single question, best first.

        Each line carries the score, the ``file_path`` as it appears in the
        corpus and the character range, which is what identifies a source.

        Args:
            query: Question to search for; it cannot be empty.
            k: Maximum number of sources to print.
            index_path: SQLite index to search, built by ``index``.
            retriever: ``bm25`` for the lexical search (default),
                ``semantic`` for the embeddings of ``index --semantic``, or
                ``hybrid`` to fuse both with Reciprocal Rank Fusion.
            vectors_path: Where the vectors live, for ``semantic`` and
                ``hybrid``.
        """
        if retriever == "bm25":
            results = run_search(query, k, index_path, self._index_store)
        elif retriever == "semantic":
            results = run_semantic_search(
                query,
                k,
                index_path,
                vectors_path,
                self._index_store,
                self._vector_store,
                self._load_embedder
            )
        elif retriever == "hybrid":
            results = run_hybrid_search(
                query,
                k,
                index_path,
                vectors_path,
                self._index_store,
                self._vector_store,
                self._load_embedder
            )
        else:
            raise ValueError(
                "retriever must be 'bm25', 'semantic' or 'hybrid'"
            )
        if not results:
            print("No sources found.")
        for position, (source, score) in enumerate(results, start=1):
            print(
                f"{position}.  "
                f"{score:.2f}  "
                f"{source.file_path}  "
                f"[{source.first_character_index}:"
                f"{source.last_character_index}]"
            )

    def search_dataset(
        self,
        dataset_path: str,
        k: int = 10,
        save_directory: str = "data/output/search_results",
        index_path: str = DEFAULT_INDEX_PATH
    ) -> None:
        """Search every question of a dataset and save the results.

        The index is loaded once for the whole dataset, so searching 200
        questions costs barely more than searching one.

        Args:
            dataset_path: Path to the JSON dataset of questions.
            k: Number of sources to return per question.
            save_directory: Directory where the results file is written.
            index_path: SQLite index to search, built by ``index``.
        """
        output_path = run_search_dataset(
            dataset_path,
            k,
            save_directory,
            index_path,
            self._index_store,
            self._datasets
        )
        print(f"Saved student_search_results to {output_path}")

    def answer(
        self,
        query: str,
        k: int = 10,
        index_path: str = DEFAULT_INDEX_PATH
    ) -> None:
        """Answer a single question using the retrieved sources.

        Qwen is loaded only when sources are found, so a rejected question
        or an empty search ends in under a second.

        Args:
            query: Question to answer; it cannot be empty.
            k: Number of sources retrieved for the model.
            index_path: SQLite index to search, built by ``index``.
        """
        answer = run_answer(
            query,
            k,
            index_path,
            self._index_store,
            self._corpus,
            self._load_generator
        )
        print(answer)

    def answer_dataset(
        self,
        student_search_results_path: str,
        save_directory: str = "data/output/search_results_and_answer"
    ) -> None:
        """Generate answers for saved search results and save them.

        The model is loaded once for the whole file.

        Args:
            student_search_results_path: Path to the search results file.
            save_directory: Directory where the answers file is written.
        """
        result = run_answer_dataset(
            student_search_results_path,
            save_directory,
            self._datasets,
            self._corpus,
            self._load_generator
        )
        count = result.question_count
        print(
            f"Loaded {count} questions ... "
            f"Processed {count} of {count} questions"
        )
        print(
            f"Saved student_search_results_and_answer to {result.output_path}"
        )

    def evaluate(
        self,
        student_search_results_path: str,
        dataset_path: str
    ) -> None:
        """Print recall@1/3/5/10 and the MRR of search results.

        The recall line has the format of the subject's example, so it can be
        compared at a glance with the reference tool; the MRR goes on a
        second line.

        Args:
            student_search_results_path: Path to the search results file.
            dataset_path: Path to the dataset with the correct sources.
        """
        evaluation = run_evaluate(
            student_search_results_path, dataset_path, self._datasets
        )
        parts = [
            f"Recall@{k}: {recall:.3f}"
            for k, recall in evaluation.recalls.items()
        ]
        print(" ".join(parts))
        print(f"MRR: {evaluation.mrr:.3f}")


def usage_error(component: object, words: list[str]) -> str | None:
    """Check the command and its flags before anything is executed.

    Fire runs the command first and only then complains about a flag it
    could not consume, so a typo would cost a full re-index. Checking here
    stops it before any work starts.

    Args:
        component: Object whose public methods are the commands.
        words: Command-line words, without the program name.

    Returns:
        A message describing the problem, or ``None`` when the words are
        fine (or when Fire itself should handle them, as with ``--help``).
    """
    if not words or words[0].startswith("-") or "--help" in words:
        return None
    commands = sorted(
        name for name in dir(component)
        if not name.startswith("_") and callable(getattr(component, name))
    )
    if words[0] not in commands:
        return (
            f"unknown command '{words[0]}'. "
            f"Valid commands: {', '.join(commands)}"
        )
    parameters = inspect.signature(getattr(component, words[0])).parameters
    # An unbound method still lists "self"; it is not a flag.
    valid = [name for name in parameters if name != "self"]
    for word in words[1:]:
        if word == "--":
            break
        # Only a number such as -1 is a value. Anything else that starts
        # with "-" is a flag, even with spaces: a single token like
        # "--index_path X --k 3" must never slip through to Fire.
        if not word.startswith("-") or _is_number(word):
            continue
        # ponytail: extra positional words are not checked (Fire reports
        # them after running); telling them from flag values needs the
        # command's types.
        name = word.lstrip("-").split("=")[0].replace("-", "_")
        # Fire spells a False boolean as --noflag.
        if name in valid or name.removeprefix("no") in valid:
            continue
        return (
            f"unknown flag '{word}' for command '{words[0]}'. Valid flags: "
            f"{', '.join('--' + flag for flag in valid)}. "
            "A value that starts with '-' must be written --flag=value."
        )
    return None


def _is_number(word: str) -> bool:
    """Tell whether a word is a number such as ``-1`` or ``-0.5``.

    Args:
        word: One command-line word.

    Returns:
        ``True`` when ``float`` can read it.
    """
    try:
        float(word)
    except ValueError:
        return False
    return True


def run(component: object, argv: list[str] | None = None) -> int:
    """Run a Fire CLI and turn any failure into a clean exit code.

    This is the error boundary: no exception reaches the user as a
    traceback. An unknown command or flag is rejected before Fire runs
    anything. Fire's own usage errors (``SystemExit``) are not caught, so
    Fire still prints its usage message and exits with code 2.

    Args:
        component: Object whose public methods are exposed as commands.
        argv: Command-line words; ``None`` reads the real terminal.

    Returns:
        ``EXIT_SUCCESS`` when the command finishes, ``EXIT_ERROR`` when it
        raises an exception, ``EXIT_USAGE`` for an unknown command or flag,
        or ``EXIT_INTERRUPTED`` on Ctrl+C.
    """
    words = sys.argv[1:] if argv is None else argv
    problem = usage_error(component, words)
    if problem:
        print(f"ERROR: {problem}", file=sys.stderr)
        return EXIT_USAGE
    try:
        fire.Fire(component, command=argv, name="src")
        return EXIT_SUCCESS
    except Exception as error:
        message: str = str(error)
        if not message:
            message = type(error).__name__
        print(f"ERROR: {message}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED
