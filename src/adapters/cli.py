"""Command-line interface built with Python Fire.

Each public method of ``RagCli`` becomes a command, and each parameter
becomes a flag with the same name (``k`` becomes ``--k``).
"""

import sys
from pathlib import Path

import fire

from src.application.evaluate import run_evaluate
from src.application.index_corpus import run_index, MAX_CHUNK_SIZE
from src.application.search import run_search
from src.application.search_dataset import run_search_dataset


# Exit codes follow Unix conventions: 130 is 128 + SIGINT (signal 2), the
# code a program ends with when the user presses Ctrl+C.
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130


class RagCli:
    """Commands required by the subject, exposed through Fire.

    ``answer`` and ``answer_dataset`` are still placeholders that only report
    they are not implemented yet.
    """
    def index(
        self,
        max_chunk_size: int = MAX_CHUNK_SIZE,
        raw_directory: str = "data/raw",
        index_path: str = "data/processed/index.db"
    ) -> None:
        """Chunk the corpus and store the chunks in the index.

        Args:
            max_chunk_size: Maximum characters per chunk, from 1 to
                ``MAX_CHUNK_SIZE``.
            raw_directory: Folder of the corpus to index.
            index_path: Where the SQLite index is written.
        """
        run_index(raw_directory, max_chunk_size, index_path)
        print(
            f"Ingestion complete! Indices saved under "
            f"{Path(index_path).parent}/"
        )

    def search(
        self,
        query: str,
        k: int = 10,
        index_path: str = "data/processed/index.db"
    ) -> None:
        """Print the best sources for a single question, best first.

        Each line carries the score, the ``file_path`` as it appears in the
        corpus and the character range, which is what identifies a source.

        Args:
            query: Question to search for; it cannot be empty.
            k: Maximum number of sources to print.
            index_path: SQLite index to search, built by ``index``.
        """
        results = run_search(query, k, index_path)
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
        index_path: str = "data/processed/index.db"
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
            index_path
        )
        print(f"Saved student_search_results to {output_path}")

    def answer(self, query: str, k: int = 10) -> None:
        """Answer a single question using the retrieved sources.

        Args:
            query: Question to answer.
            k: Number of sources given to the model as context.
        """
        print("answer: not implemented yet")

    def answer_dataset(
        self,
        student_search_results_path: str,
        save_directory: str = "data/output/search_results_and_answer"
    ) -> None:
        """Generate answers for saved search results and save them.

        Args:
            student_search_results_path: Path to the search results file.
            save_directory: Directory where the answers file is written.
        """
        print("answer_dataset: not implemented yet")

    def evaluate(
        self,
        student_search_results_path: str,
        dataset_path: str
    ) -> None:
        """Print recall@1/3/5/10 of search results against a dataset.

        The line has the format of the subject's example, so it can be
        compared at a glance with the reference tool.

        Args:
            student_search_results_path: Path to the search results file.
            dataset_path: Path to the dataset with the correct sources.
        """
        recalls = run_evaluate(student_search_results_path, dataset_path)
        parts = [f"Recall@{k}: {recall:.3f}" for k, recall in recalls.items()]
        print(" ".join(parts))


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


def main() -> int:
    """Run the RAG command-line interface.

    Returns:
        The exit code, to be passed to ``sys.exit``.
    """
    return run(RagCli())
