"""Port: the question datasets and the result files of the subject."""

from pathlib import Path
from typing import Protocol

from src.domain.models import (
    RagDataset,
    StudentSearchResults,
    StudentSearchResultsAndAnswer
)


class DatasetStore(Protocol):
    """Read datasets and search results, write results.

    A port because these files are the system's input and output: JSON on
    disk for the CLI, while the HTTP API (bonus) would send them over the
    network.
    """

    def load_dataset(self, path: Path) -> RagDataset:
        """Read and validate a dataset of questions.

        Args:
            path: Where the dataset is.

        Returns:
            The validated dataset.

        Raises:
            ValueError: If it is missing, unreadable or malformed.
        """
        ...

    def load_search_results(self, path: Path) -> StudentSearchResults:
        """Read and validate the output of ``search_dataset``.

        Args:
            path: Where the results are.

        Returns:
            The validated search results.

        Raises:
            ValueError: If they are missing, unreadable or malformed.
        """
        ...

    def write_results(
        self,
        results: StudentSearchResults | StudentSearchResultsAndAnswer,
        path: Path
    ) -> None:
        """Write search results, with or without answers.

        Args:
            results: What to write.
            path: Where to write it; missing folders are created.

        Raises:
            ValueError: If it cannot be written.
        """
        ...

    def check_save_directory(self, directory: Path) -> None:
        """Reject a save directory that is, or looks like, a file.

        Called before any long work, so a typo does not cost a full run.

        Args:
            directory: The folder where results will be written.

        Raises:
            ValueError: If it is an existing file or has a file suffix.
        """
        ...
