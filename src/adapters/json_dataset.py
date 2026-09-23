"""Read question datasets from JSON files on disk."""

import json
from pathlib import Path

from pydantic import ValidationError

from src.domain.models import RagDataset


def load_dataset(path: Path) -> RagDataset:
    """Read a JSON file and validate it as a ``RagDataset``.

    Every failure is turned into a ``ValueError`` with a one-line message
    that names the file; the original error is kept as its cause.

    Args:
        path: Path of the dataset file.

    Returns:
        The validated dataset.

    Raises:
        ValueError: If the file does not exist, cannot be read, is not valid
            JSON, or does not have the shape of a dataset.
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
