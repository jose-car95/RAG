"""Read and write search results as JSON files on disk."""

import json
from pathlib import Path

from pydantic import ValidationError

from src.domain.models import StudentSearchResults


def write_search_results(
    results: StudentSearchResults,
    output_path: Path
) -> None:
    """Write search results as indented JSON, creating missing folders.

    Args:
        results: Search results to write.
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


def load_search_results(path: Path) -> StudentSearchResults:
    """Read a JSON file and validate it as ``StudentSearchResults``.

    Same contract as ``load_dataset``: every failure becomes a one-line
    ``ValueError`` that names the file, with the original error as cause.

    Args:
        path: Path of the search results file.

    Returns:
        The validated search results.

    Raises:
        ValueError: If the file does not exist, cannot be read, is not valid
            JSON, or does not have the shape of search results.
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
