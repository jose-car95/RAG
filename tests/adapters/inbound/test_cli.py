"""End-to-end tests for the command-line entry point.

The CLI is run in a subprocess, exactly as the subject invokes it
(``python -m src <command>``), so these tests see the real exit code and the
real stdout/stderr instead of calling Python functions directly.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

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


def test_answer_dataset_reports_missing_results(tmp_path: Path) -> None:
    """A missing input file ends in a one-line error, without the model."""
    missing = tmp_path / "results.json"

    result = run_cli(
        "answer_dataset",
        "--student_search_results_path",
        str(missing),
        "--save_directory",
        str(tmp_path / "answers"),
    )

    assert result.returncode == 1
    assert result.stderr == f"ERROR: search results not found: {missing}\n"


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


def make_tiny_index(tmp_path: Path) -> Path:
    """Build an index of its own, so the test needs no local state.

    The real ``data/processed/index.db`` is generated and never committed, so
    a test that relied on it passed here and failed in CI.

    Args:
        tmp_path: Temporary folder provided by pytest.

    Returns:
        Path of the index.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "notes.md").write_text(
        "# Endpoints\nThe http endpoint loads a lora adapter.\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "index.db"
    run_cli(
        "index", "--raw_directory", str(corpus),
        "--index_path", str(index_path),
    )
    return index_path


def test_search_dataset_writes_results_file(tmp_path: Path) -> None:
    """The results file is written and its path is reported."""
    index_path = make_tiny_index(tmp_path)

    result = run_cli(
        "search_dataset",
        "--dataset_path",
        "data/datasets/UnansweredQuestions/dataset_docs_public.json",
        "--k",
        "10",
        "--save_directory",
        str(tmp_path),
        "--index_path",
        str(index_path),
    )

    output_path = tmp_path / "dataset_docs_public.json"
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"Saved student_search_results to {output_path}\n"
    )
    assert output_path.is_file()


def test_search_dataset_uses_default_save_directory(tmp_path: Path) -> None:
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
        "--index_path",
        str(make_tiny_index(tmp_path)),
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


def test_search_prints_the_ranked_sources(tmp_path: Path) -> None:
    """``search`` prints one numbered line per source, best first."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "b.md").write_text(
        "# Endpoints\nThe http endpoint loads a lora adapter.\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "index.db"
    run_cli(
        "index", "--raw_directory", str(corpus),
        "--index_path", str(index_path),
    )

    result = run_cli(
        "search", "http endpoint", "--k", "5",
        "--index_path", str(index_path),
    )

    assert result.returncode == 0, result.stderr
    first_line = result.stdout.splitlines()[0]
    assert first_line.startswith("1. ")
    assert str(corpus / "b.md") in first_line
    assert "[0:" in first_line


def test_search_rejects_an_empty_query(tmp_path: Path) -> None:
    """``search ""`` is a user error, not an empty result."""
    result = run_cli("search", "", "--index_path", str(tmp_path / "index.db"))

    assert result.returncode == 1
    assert result.stderr == "ERROR: query must not be empty\n"


def test_search_reports_a_missing_index(tmp_path: Path) -> None:
    """Searching before indexing says what to run."""
    index_path = tmp_path / "index.db"

    result = run_cli("search", "lora", "--index_path", str(index_path))

    assert result.returncode == 1
    assert result.stderr == (
        f"ERROR: index not found: {index_path}; run index first\n"
    )
    assert not index_path.exists()


def test_search_says_when_nothing_is_found(tmp_path: Path) -> None:
    """A query with no match prints a message instead of nothing."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "b.md").write_text("# Endpoints\n", encoding="utf-8")
    index_path = tmp_path / "index.db"
    run_cli(
        "index", "--raw_directory", str(corpus),
        "--index_path", str(index_path),
    )

    result = run_cli(
        "search", "kubernetes", "--index_path", str(index_path)
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "No sources found.\n"


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


def test_evaluate_prints_recall_in_the_subject_format(tmp_path: Path) -> None:
    """One line with Recall@1/3/5/10 and three decimals, as in the subject."""
    correct = {
        "file_path": "data/raw/vllm-0.10.1/docs/features/lora.md",
        "first_character_index": 4695,
        "last_character_index": 6098,
    }
    wrong = dict(correct, first_character_index=0, last_character_index=10)
    dataset = tmp_path / "dataset.json"
    dataset.write_text(
        json.dumps({
            "rag_questions": [
                {
                    "question_id": question_id,
                    "question": "How to load a lora adapter?",
                    "sources": [correct],
                    "answer": "With the endpoint.",
                }
                for question_id in ("q1", "q2")
            ]
        }),
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({
            "search_results": [
                {
                    "question_id": "q1",
                    "question": "How to load a lora adapter?",
                    "retrieved_sources": [correct],
                },
                {
                    "question_id": "q2",
                    "question": "How to load a lora adapter?",
                    "retrieved_sources": [wrong, wrong, wrong, correct],
                },
            ],
            "k": 10,
        }),
        encoding="utf-8",
    )

    result = run_cli(
        "evaluate",
        "--student_search_results_path",
        str(results),
        "--dataset_path",
        str(dataset),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "Recall@1: 0.500 Recall@3: 0.500 Recall@5: 1.000 Recall@10: 1.000\n"
        "MRR: 0.625\n"
    )


def test_evaluate_reports_missing_search_results(tmp_path: Path) -> None:
    """A missing results file ends in a one-line error and exit code 1."""
    missing = tmp_path / "nope.json"

    result = run_cli(
        "evaluate",
        "--student_search_results_path",
        str(missing),
        "--dataset_path",
        "data/datasets/AnsweredQuestions/dataset_docs_public.json",
    )

    assert result.returncode == 1
    assert result.stderr == f"ERROR: search results not found: {missing}\n"


def test_cli_import_does_not_load_torch() -> None:
    """``--help``, ``index`` and ``search`` must not pay for torch's import.

    Only ``answer`` needs the model, so torch is imported inside
    ``load_generator``; importing the whole wiring, which plugs in the Qwen
    adapter, must leave it out.
    """
    code = (
        "import sys\n"
        "import src.bootstrap\n"
        "print('torch' in sys.modules, 'transformers' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False False"


@pytest.mark.parametrize(
    ("query", "k", "message"),
    [
        ("", "10", "query must not be empty"),
        ("What is vLLM?", "0", "k must be a positive integer"),
    ],
)
def test_answer_rejects_bad_arguments(
    tmp_path: Path, query: str, k: str, message: str
) -> None:
    """A one-line error and exit code 1, as for ``search``."""
    index_path = make_tiny_index(tmp_path)

    result = run_cli(
        "answer", query, "--k", k, "--index_path", str(index_path)
    )

    assert result.returncode == 1
    assert result.stderr == f"ERROR: {message}\n"


def test_answer_without_sources_says_so(tmp_path: Path) -> None:
    """Nothing retrieved: the user is told, and it is not an error."""
    index_path = make_tiny_index(tmp_path)

    result = run_cli(
        "answer", "asdfghjkl", "--k", "10", "--index_path", str(index_path)
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "No sources found, so the question cannot be answered.\n"
    )


def test_answer_reports_missing_index(tmp_path: Path) -> None:
    """A missing index ends in the same error as ``search``."""
    missing = tmp_path / "missing.db"

    result = run_cli("answer", "lora", "--index_path", str(missing))

    assert result.returncode == 1
    assert result.stderr.startswith(f"ERROR: index not found: {missing}")


@pytest.mark.skipif(
    not (REPO_ROOT / ".cache/huggingface/models--Qwen--Qwen3-0.6B").is_dir()
    or not (REPO_ROOT / "data/processed/index.db").is_file(),
    reason="needs the Qwen weights and the real index",
)
def test_answer_uses_the_real_sources_and_model() -> None:
    """End to end, with Qwen on CPU: the answer names the real endpoint."""
    result = run_cli(
        "answer", "How do I dynamically load a LoRA adapter in vLLM?",
        "--k", "10",
    )

    assert result.returncode == 0, result.stderr
    assert "load_lora_adapter" in result.stdout
