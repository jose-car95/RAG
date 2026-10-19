"""Read and write the subject's JSON files: datasets and search results."""

import json
from pathlib import Path

from pydantic import ValidationError

from src.application.ports.dataset_store import DatasetStore
from src.domain.models import (
    RagDataset,
    StudentSearchResults,
    StudentSearchResultsAndAnswer
)


class JsonDatasetStore(DatasetStore):
    """The ``DatasetStore`` port on JSON files on disk.

    Every failure becomes a ``ValueError`` with a one-line message that names
    the file; the original error is kept as its cause.
    """

    def load_dataset(self, path: Path) -> RagDataset:
        """Read a JSON file and validate it as a ``RagDataset``.

        Args:
            path: Path of the dataset file.

        Returns:
            The validated dataset.

        Raises:
            ValueError: If the file does not exist, cannot be read, is not
                valid JSON, or does not have the shape of a dataset.
        """
        try:
            with open(path, encoding="UTF-8") as file:
                raw_data = json.load(file)
                dataset = RagDataset.model_validate(raw_data)
                return dataset

        except FileNotFoundError as error:
            raise ValueError(f"dataset not found: {path}") from error

        except OSError as error:
            raise ValueError(f"cannot read dataset: {path}") from error

        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(f"dataset is not valid JSON: {path}") from error

        except ValidationError as error:
            raise ValueError(
                f"dataset does not match the expected format: {path}"
            ) from error

    def load_search_results(self, path: Path) -> StudentSearchResults:
        """Read a JSON file and validate it as ``StudentSearchResults``.

        Args:
            path: Path of the search results file.

        Returns:
            The validated search results.

        Raises:
            ValueError: If the file does not exist, cannot be read, is not
                valid JSON, or does not have the shape of search results.
        """
        try:
            with open(path, encoding="UTF-8") as file:
                raw_data = json.load(file)
                results = StudentSearchResults.model_validate(raw_data)
                return results

        except FileNotFoundError as error:
            raise ValueError(f"search results not found: {path}") from error

        except OSError as error:
            raise ValueError(f"cannot read search results: {path}") from error

        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(
                f"search results are not valid JSON: {path}"
            ) from error

        except ValidationError as error:
            raise ValueError(
                f"search results do not match the expected format: {path}"
            ) from error

    def write_results(
        self,
        results: StudentSearchResults | StudentSearchResultsAndAnswer,
        output_path: Path
    ) -> None:
        """Write search results as indented JSON, creating missing folders.

        Args:
            results: Search results to write, with or without answers.
            output_path: File to create or overwrite.

        Raises:
            ValueError: If the folders or the file cannot be written.
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, mode="w", encoding="UTF-8") as file:
                file.write(results.model_dump_json(indent=2))

        except OSError as error:
            raise ValueError(
                f"cannot write search results: {output_path}"
            ) from error
