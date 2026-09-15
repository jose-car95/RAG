"""Command-line interface built with Python Fire.

Each public method of ``RagCli`` becomes a command, and each parameter
becomes a flag with the same name (``k`` becomes ``--k``).
"""

import fire


class RagCli:
    """Commands required by the subject, exposed through Fire.

    For now every command is a placeholder that only reports it is not
    implemented yet.
    """

    def index(self, max_chunk_size: int = 2000) -> None:
        """Build the search index from the corpus in ``data/raw/``.

        Args:
            max_chunk_size: Maximum number of characters per chunk.
        """
        print("index: not implemented yet")

    def search(self, query: str, k: int = 10) -> None:
        """Return the top-k sources for a single question.

        Args:
            query: Question to search for.
            k: Number of sources to return.
        """
        print("search: not implemented yet")

    def search_dataset(
        self,
        dataset_path: str,
        k: int = 10,
        save_directory: str = "data/output/search_results"
    ) -> None:
        """Search every question of a dataset and save the results.

        Args:
            dataset_path: Path to the JSON dataset of questions.
            k: Number of sources to return per question.
            save_directory: Directory where the results file is written.
        """
        print("search_dataset: not implemented yet")

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
        """Report recall@k of search results against a reference dataset.

        Args:
            student_search_results_path: Path to the search results file.
            dataset_path: Path to the dataset with the correct sources.
        """
        print("evaluate: not implemented yet")


def main() -> None:
    """Run the command-line interface."""
    fire.Fire(RagCli())
