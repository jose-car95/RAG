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


def _json_position(error: json.JSONDecodeError) -> str:
    """Describe where a JSON text breaks.

    Args:
        error: The error raised while parsing.

    Returns:
        The line, the column and the parser's reason.
    """
    return f"line {error.lineno}, column {error.colno}: {error.msg}"


def _first_problem(error: ValidationError) -> str:
    """Describe the first field that does not match the model.

    Only the first problem is shown, so the message stays on one line.

    Args:
        error: The error raised while validating.

    Returns:
        The dotted path of the field and the reason, or only the reason
        when the whole document has the wrong type.
    """
    problem = error.errors()[0]
    field = ".".join(str(part) for part in problem["loc"])
    if not field:
        return problem["msg"]
    return f"{field}: {problem['msg']}"


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

        except json.JSONDecodeError as error:
            raise ValueError(
                f"dataset is not valid JSON: {path} ({_json_position(error)})"
            ) from error

        except UnicodeDecodeError as error:
            raise ValueError(f"dataset is not valid JSON: {path}") from error

        except ValidationError as error:
            raise ValueError(
                "dataset does not match the expected format: "
                f"{path} ({_first_problem(error)})"
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

        except json.JSONDecodeError as error:
            raise ValueError(
                "search results are not valid JSON: "
                f"{path} ({_json_position(error)})"
            ) from error

        except UnicodeDecodeError as error:
            raise ValueError(
                f"search results are not valid JSON: {path}"
            ) from error

        except ValidationError as error:
            raise ValueError(
                "search results do not match the expected format: "
                f"{path} ({_first_problem(error)})"
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

    def check_save_directory(self, directory: Path) -> None:
        """Reject a save directory that is, or looks like, a file.

        A name with a suffix such as ``out.json`` is taken as a file, so a
        folder named ``results.v2`` is refused too; the message says why.

        Args:
            directory: The folder where results will be written.

        Raises:
            ValueError: If it is an existing file or has a file suffix.
        """
        if directory.suffix or directory.is_file():
            raise ValueError(
                f"save directory must be a folder, not a file: {directory}"
            )
