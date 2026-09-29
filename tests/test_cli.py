"""End-to-end tests for the command-line entry point.

The CLI is run in a subprocess, exactly as the subject invokes it
(``python -m src <command>``), so these tests see the real exit code and the
real stdout/stderr instead of calling Python functions directly.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_COMMANDS = (
    "index",
    "search",
    "search_dataset",
    "answer",
    "answer_dataset",
    "evaluate",
)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run ``python -m src`` with the given arguments from the repo root.

    Args:
        *args: Command-line arguments passed after ``python -m src``.

    Returns:
        The finished process, with decoded stdout and stderr.
    """
    return subprocess.run(
        [sys.executable, "-m", "src", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_help_lists_required_commands() -> None:
    """``--help`` lists every command required by the subject."""
    result = run_cli("--help")
    # Fire writes its help to stderr when the output is not a terminal.
    output = result.stdout + result.stderr

    assert result.returncode == 0, result.stderr
    for command in REQUIRED_COMMANDS:
        # One command per line, so "search" is not matched by "search_dataset".
        assert re.search(rf"^\s+{command}$", output, re.MULTILINE), output


@pytest.mark.parametrize(
    "args",
    [
        ("search", "What is vLLM?", "--k", "10"),
        ("answer", "What is vLLM?", "--k", "10"),
        (
            "answer_dataset",
            "--student_search_results_path",
            "results.json",
            "--save_directory",
            "answers",
        ),
        (
            "evaluate",
            "--student_search_results_path",
            "results.json",
            "--dataset_path",
            "dataset.json",
        ),
    ],
    ids=lambda args: args[0],
)
def test_stub_reports_not_implemented(args: tuple[str, ...]) -> None:
    """Each command accepts its subject flags and reports it is a stub."""
    result = run_cli(*args)

    assert result.returncode == 0, result.stderr
    assert f"{args[0]}: not implemented yet" in result.stdout
    assert "Traceback" not in result.stderr


def test_usage_error_names_the_program() -> None:
    """Fire's usage messages name the program ``src``, not ``__main__.py``."""
    result = run_cli("nonexistent_command")

    assert result.returncode == 2
    assert "Usage: src <command>" in result.stderr
    assert "Traceback" not in result.stderr


def test_search_dataset_reports_missing_dataset() -> None:
    """A missing dataset ends in a one-line error and exit code 1."""
    result = run_cli(
        "search_dataset",
        "--dataset_path",
        "/nonexistent/dataset.json",
        "--k",
        "10",
    )

    assert result.returncode == 1
    assert result.stderr == (
        "ERROR: dataset not found: /nonexistent/dataset.json\n"
    )


def test_search_dataset_writes_results_file(tmp_path: Path) -> None:
    """The results file is written and its path is reported."""
    result = run_cli(
        "search_dataset",
        "--dataset_path",
        "data/datasets/UnansweredQuestions/dataset_docs_public.json",
        "--k",
        "10",
        "--save_directory",
        str(tmp_path),
    )

    output_path = tmp_path / "dataset_docs_public.json"
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"Saved student_search_results to {output_path}\n"
    )
    assert output_path.is_file()


def test_search_dataset_uses_default_save_directory() -> None:
    """Without ``--save_directory`` the file goes to the default folder."""
    output_path = (
        REPO_ROOT / "data/output/search_results/dataset_code_public.json"
    )
    output_path.unlink(missing_ok=True)

    result = run_cli(
        "search_dataset",
        "--dataset_path",
        "data/datasets/UnansweredQuestions/dataset_code_public.json",
        "--k",
        "10",
    )

    assert result.returncode == 0, result.stderr
    assert output_path.is_file()
    output_path.unlink()


def test_search_dataset_rejects_invalid_k() -> None:
    """A ``k`` that is not a positive integer is a usage error."""
    result = run_cli(
        "search_dataset",
        "--dataset_path",
        "data/datasets/UnansweredQuestions/dataset_docs_public.json",
        "--k",
        "0",
    )

    assert result.returncode == 1
    assert result.stderr == "ERROR: k must be a positive integer\n"


def test_index_reports_missing_corpus_folder() -> None:
    """A missing corpus folder ends in a one-line error and exit code 1."""
    result = run_cli("index", "--raw_directory", "/nonexistent")

    assert result.returncode == 1
    assert result.stderr == "ERROR: corpus folder not found: /nonexistent\n"


def test_index_rejects_an_invalid_max_chunk_size(tmp_path: Path) -> None:
    """``index`` reports an invalid chunk width and writes no index."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.py").write_text("x = 1\n", encoding="utf-8")
    index_path = tmp_path / "index.db"

    result = run_cli(
        "index",
        "--raw_directory",
        str(corpus),
        "--index_path",
        str(index_path),
        "--max_chunk_size",
        "0",
    )

    assert result.returncode == 1
    assert result.stderr == (
        "ERROR: max_chunk_size must be an integer between 1 and 2000\n"
    )
    assert not index_path.exists()


def test_index_writes_the_index_file(tmp_path: Path) -> None:
    """``index`` chunks the corpus and reports where the index was saved."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    source = "def first() -> int:\n    return 1\n"
    (corpus / "a.py").write_text(source, encoding="utf-8")
    index_path = tmp_path / "processed" / "index.db"

    result = run_cli(
        "index",
        "--raw_directory",
        str(corpus),
        "--index_path",
        str(index_path),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"Ingestion complete! Indices saved under {index_path.parent}/\n"
    )
    assert index_path.is_file()
