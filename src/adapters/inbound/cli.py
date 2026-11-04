"""Command-line interface built with Python Fire.

Each public method of ``RagCli`` becomes a command, and each parameter
becomes a flag with the same name (``k`` becomes ``--k``).
"""

import sys
from pathlib import Path

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
from src.application.use_cases.embed_index import run_embed_index
from src.application.use_cases.index_corpus import run_index, MAX_CHUNK_SIZE
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
EXIT_INTERRUPTED = 130

# Default store locations, under data/processed/. Kept here so the four
# commands that read the index, and the two that read the vectors, all point
# at the same place and a change touches one line.
DEFAULT_INDEX_PATH = "data/processed/index.db"
DEFAULT_VECTORS_PATH = "data/processed/embeddings.db"


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
        embeddings: bool = False,
        vectors_path: str = DEFAULT_VECTORS_PATH
    ) -> None:
        """Chunk the corpus and store the chunks in the index.

        Args:
            max_chunk_size: Maximum characters per chunk, from 1 to
                ``MAX_CHUNK_SIZE``.
            raw_directory: Folder of the corpus to index.
            index_path: Where the SQLite index is written.
            embeddings: Also store a semantic vector per chunk text (bonus).
            vectors_path: Where the vectors are written.
        """
        chunk_count = run_index(
            raw_directory,
            max_chunk_size,
            index_path,
            self._corpus,
            self._index_store
        )
        print(
            f"Ingestion complete! Indexed {chunk_count} chunks under "
            f"{Path(index_path).parent}/"
        )

        if embeddings:
            new, total = run_embed_index(
                index_path,
                vectors_path,
                self._index_store,
                self._vector_store,
                self._load_embedder
            )
            print(
                f"Embeddings ready! {new} new of {total} chunk texts under "
                f"{Path(vectors_path).parent}/"
            )

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
                ``semantic`` for the embeddings of ``index --embeddings``, or
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


def run(component: object, argv: list[str] | None = None) -> int:
    """Run a Fire CLI and turn any failure into a clean exit code.

    This is the error boundary: no exception reaches the user as a
    traceback. Fire's own usage errors (``SystemExit``) are not caught, so
    Fire still prints its usage message and exits with code 2.

    Args:
        component: Object whose public methods are exposed as commands.
        argv: Command-line words; ``None`` reads the real terminal.

    Returns:
        ``EXIT_SUCCESS`` when the command finishes, ``EXIT_ERROR`` when it
        raises an exception, or ``EXIT_INTERRUPTED`` on Ctrl+C.
    """
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
