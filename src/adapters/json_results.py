"""Write search results to JSON files on disk."""

from pathlib import Path

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
