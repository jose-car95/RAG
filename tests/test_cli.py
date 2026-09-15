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
        ("index", "--max_chunk_size", "2000"),
        ("search", "What is vLLM?", "--k", "10"),
        (
            "search_dataset",
            "--dataset_path",
            "data/datasets/UnansweredQuestions/dataset_docs_public.json",
            "--k",
            "10",
            "--save_directory",
            "data/output/search_results/UnansweredQuestions",
        ),
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
